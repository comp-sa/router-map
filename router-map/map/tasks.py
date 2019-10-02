import logging

from celery.task import periodic_task
from django.db import transaction
from easysnmp import exceptions, Session
from celery.schedules import crontab
from map.models import Device, Connection, Interface
from django.conf import settings
from map import redis_client
from django.contrib.gis.geos import Point


logger = logging.getLogger('maps')


class SnmpManager:
    __dict__ = {}

    def __init__(self):
        all_hosts = Device.objects.only('pk', 'ip_address', 'snmp_community')
        for host in all_hosts:
            snmp_session = Session(hostname=host.ip_address, community=host.snmp_community, version=2)
            self.__dict__[host.pk] = snmp_session

    def get_chassisid(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            return snmp_session.get('iso.0.8802.1.1.2.1.3.2.0').value
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()

    def get_name(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            return snmp_session.get('iso.3.6.1.2.1.1.5.0').value
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()

    def get_location(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            return snmp_session.get('iso.3.6.1.2.1.1.6.0').value
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()

    def get_interfaces_info(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            interface_numbers = snmp_session.bulkwalk('iso.3.6.1.2.1.2.2.1.1')
            interface_names = snmp_session.bulkwalk('iso.3.6.1.2.1.2.2.1.2')
            interface_speeds = snmp_session.bulkwalk('iso.3.6.1.2.1.31.1.1.1.15')
            return [(i.value, j.value, int(k.value) / 1000)
                    for i, j, k in zip(interface_numbers, interface_names, interface_speeds)]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()
            return []

    def get_aggregate_interfaces(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            aggregate_interfaces = snmp_session.bulkwalk('iso.2.840.10006.300.43.1.2.1.1.12')
            return [(i.value, i.oid.split('.')[-1]) for i in aggregate_interfaces]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()
            return []

    def get_logical_physical_connection(self, device, port_number):
        try:
            snmp_session = self.__dict__[device.pk]
            connections = snmp_session.bulkwalk('iso.3.6.1.2.1.31.1.2.1.3.' + port_number)
            return [i.oid.split('.')[-1] for i in connections]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()
            return []

    def get_neighbours_info(self, device):
        try:
            snmp_session = self.__dict__[device.pk]
            neighbour_chassisids = snmp_session.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.5')
            neighbour_interfaces = snmp_session.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.7')
            return [(i.value, i.oid.split('.')[-2], j.value) for i, j in
                    zip(neighbour_chassisids, neighbour_interfaces)]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
            device.snmp_connection = False
            device.save()
            return []


@periodic_task(run_every=(crontab(minute=f"*/{settings.TASK_PERIOD}")))
def check_connections():
    snmp_manager = SnmpManager()
    with transaction.atomic():
        all_hosts = Device.objects.only('pk', 'ip_address', 'snmp_community')
        host_chassisid_dictionary = {}

        for host in all_hosts:
            check_chassisid(snmp_manager, host, host_chassisid_dictionary)

        all_hosts = Device.objects.filter(snmp_connection=True).only('pk', 'ip_address', 'snmp_community')
        Interface.objects.update(active=False)
        for host in all_hosts:
            update_name(snmp_manager, host)
            if host.point_via_snmp:
                update_location(snmp_manager, host)
            update_interfaces_info(snmp_manager, host)
            update_aggregations(snmp_manager, host)

        Connection.objects.update(active=False)
        for host in all_hosts:
            update_lldp_connections(snmp_manager, host, host_chassisid_dictionary)
        redis_client.redis_client.set_last_update_time()


def check_chassisid(snmp_manager, device, host_chassisid_dictionary):
    chassisid = snmp_manager.get_chassisid(device)
    if chassisid is not None:
        host_chassisid_dictionary[chassisid] = device.pk
        device.snmp_connection = True
        device.save()


def update_name(snmp_manager, device):
    name = snmp_manager.get_name(device)
    if name is None:
        device.name = str(device.ip_address)
    else:
        device.name = name
    device.save()


def update_location(snmp_manager, device):
    location = snmp_manager.get_location(device)
    if location is not None:
        try:
            longitude, latitude = [float(x) for x in location.split(', ')]
            device.point = Point(longitude, latitude)
            device.save()
        except (ValueError, TypeError):
            logger.warning(
                f"Wrong location format \"{location.value}\", expected: \"longitude, latitude\""
                f"(host: {device.ip_address}, pk: {device.pk})")


def update_interfaces_info(snmp_manager, device):
    interfaces = snmp_manager.get_interfaces_info(device)
    for number, name, speed in interfaces:
        interface, _ = Interface.objects.get_or_create(device=device, number=number)
        interface.speed = speed
        interface.name = name
        interface.aggregate_interface = None
        interface.active = True
        interface.save()


def update_aggregations(snmp_manager, device):
    aggregate_interfaces = snmp_manager.get_aggregate_interfaces(device)
    for aggregate_interface_number, interface_number in aggregate_interfaces:
        interface = Interface.objects.get(device=device, number=interface_number)
        aggregate_interface = Interface.objects.get(device=device, number=aggregate_interface_number)
        interface.aggregate_interface = aggregate_interface
        interface.save()
        logical_physical_connection = snmp_manager.get_logical_physical_connection(device, interface_number)
        for connection in logical_physical_connection:
            physical_interface = Interface.objects.get(device=device, number=connection)
            physical_interface.aggregate_interface = aggregate_interface
            physical_interface.save()


def update_lldp_connections(snmp_manager, device, host_chassisid_dictionary):
    neighbours = snmp_manager.get_neighbours_info(device)
    for chassisid, interface1_number, interface2_number in neighbours:
        if host_chassisid_dictionary.get(chassisid) is not None:
            if device.pk > host_chassisid_dictionary[chassisid]:
                device1 = Device.objects.get(pk=device.pk)
                device2 = Device.objects.get(pk=host_chassisid_dictionary[chassisid])
                interface1 = Interface.objects.get(device=device1, number=interface1_number)
                interface2 = Interface.objects.get(device=device2, number=interface2_number)
                connection, _ = Connection.objects.get_or_create(local_interface=interface1,
                                                                 remote_interface=interface2)
                connection.active = True
                connection.save()