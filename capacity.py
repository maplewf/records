#!/usr/bin/python

import os
from novaclient.client import Client

# Print member variable of one class
def getAllAttrs(obj):
    strAttrs = ''
    for o in dir(obj):
        strAttrs =strAttrs + o + ' := ' + str(getattr(obj,o)) + '\n'
    return strAttrs;

def get_nova_credentials_v2():
    d = {}
    d['version'] = '2'
    d['username'] = os.environ['OS_USERNAME']
    d['api_key'] = os.environ['OS_PASSWORD']
    d['auth_url'] = os.environ['OS_AUTH_URL']
    d['project_id'] = os.environ['OS_TENANT_NAME']
    d['cacert']=os.environ['OS_CACERT']
    return d

def servers_usage(hypervisors):
    servers = nova_client.servers.list()
    print "% 30s% 10s % 10s% 10s% 30s" % ('Name', 'CPU', 'RAM', 'Disk', 'hypervisor_hostname')
    total_vcpu = 0
    total_ram = 0
    total_disk = 0
    for s in servers:
        fid = s.flavor['id']
        flavor = nova_client.flavors.get(fid)
        total_vcpu += flavor.vcpus
        total_ram += flavor.ram
        total_disk += flavor.disk
        host = getattr(s, "OS-EXT-SRV-ATTR:hypervisor_hostname")
        if host:
            s.flavor_vcpus = flavor.vcpus
            if host not in hypervisors:
                hypervisors[host] = {'servers': [s]}
            else:
                hypervisors[host]['servers'].append(s)
            print "% 30s% 10d % 10d% 10d% 30s" % (s.name, flavor.vcpus, flavor.ram, flavor.disk, host)
        else:
            print "% 30s% 10d % 10d% 10d" % (s.name, flavor.vcpus, flavor.ram, flavor.disk)
    print "% 30s% 10d % 10d% 10d" % ('Total', total_vcpu, total_ram, total_disk)
    return

def short_name(host):
    nx = host.split('.')[0].split('-')
    return nx[1] + "-" + nx[2]

def cpu_layout(hypervisors):
    hosts = hypervisors.keys()
    hosts.sort(compare_name)
    line = '%-30s' % 'CPU Layout:'
    for host in hosts:
        line += "% 10s" % short_name(host)
    print line
    for host, values in hypervisors.items():
        stat_hv_t = stat_hv_u = stat_own_u = 0
        if 'hv' in values:
            stat_hv_t = values['hv'].vcpus
            stat_hv_u = values['hv'].vcpus_used
        if 'servers' in values:
            idx = hosts.index(host)
            for s in values['servers']:
                print '% 30s' % s.name + ' ' * (10 * idx) + '% 10s' % s.flavor_vcpus
                stat_own_u += s.flavor_vcpus
        hypervisors[host]['stat'] = (stat_hv_t, stat_hv_u, stat_own_u)
    print '-' * (30 + 10 * len(hosts))
    line1 = '% 30s' % 'Total:'
    line2 = '% 30s' % 'Idle:'
    for host in hosts:
        (stat_hv_t, stat_hv_u, stat_own_u) = hypervisors[host]['stat']
        if stat_hv_u == stat_own_u:
            stat_str = "%d/%d" % (stat_hv_u, stat_hv_t)
        else:
            stat_str = "%d(%d)/%d" % (stat_hv_u, stat_own_u, stat_hv_t)
        line1 += "% 10s" % stat_str
        line2 += "% 10d" % (stat_hv_t - stat_hv_u)
    print line1
    print line2

def compare_hv(x, y):
    return compare_name(x.hypervisor_hostname, y.hypervisor_hostname)

def compare_name(x, y):
    nx = x.split('.')[0].split('-')
    ny = y.split('.')[0].split('-')
    nx_shelf = int(nx[1])
    nx_slot = int(nx[2])
    ny_shelf = int(ny[1])
    ny_slot = int(ny[2])
    if nx_shelf == ny_shelf:
        if nx_slot > ny_slot:
            return 1
        elif nx_slot == ny_slot:
            return 0
        else:
            return -1
    elif nx_shelf > ny_shelf:
        return 1
    else:
        return -1

def hypervisors_usage(hypervisors):
    hvs = nova_client.hypervisors.list(detailed=True)
    hvs.sort(compare_hv)
    _vcpu_t = _vcpu_u = _vcpu_l = 0
    _mem_t = _mem_u = _mem_l = 0
    _disk_t = _disk_u = _disk_l = 0
    print "% 25s% 10s% 10s% 10s% 10s% 10s% 10s% 10s% 10s% 10s" % ('Name', 'CPU_T', 'CPU_U', '*CPU_L', 'MEM_T', 'MEM_U', '*MEM_L', 'Disk_T', 'Disk_U', '*Disk_L')
    for hv in hvs:
        if hv.hypervisor_hostname not in hypervisors:
            hypervisors[hv.hypervisor_hostname] = {'hv': hv}
        else:
            hypervisors[hv.hypervisor_hostname]['hv'] = hv
        _vcpu_t += hv.vcpus
        _vcpu_u += hv.vcpus_used
        _vcpu_l += (hv.vcpus-hv.vcpus_used)
        _mem_t += hv.memory_mb
        _mem_u += hv.memory_mb_used
        _mem_l += (hv.memory_mb-hv.memory_mb_used)
        _disk_t += hv.local_gb
        _disk_u += hv.local_gb_used
        _disk_l += (hv.local_gb-hv.local_gb_used)
        print "% 25s% 10d% 10d% 10d% 10d% 10d% 10d% 10d% 10d% 10d" % (
            hv.hypervisor_hostname, hv.vcpus, hv.vcpus_used, hv.vcpus-hv.vcpus_used,
            hv.memory_mb, hv.memory_mb_used, hv.memory_mb-hv.memory_mb_used,
            hv.local_gb, hv.local_gb_used, hv.local_gb-hv.local_gb_used)

    print "% 25s% 10d% 10d% 10d% 10d% 10d% 10d% 10d% 10d% 10d" % (
            'Total', _vcpu_t, _vcpu_u, _vcpu_l, _mem_t, _mem_u, _mem_l, _disk_t, _disk_u, _disk_l)

hypervisors = {}
credentials = get_nova_credentials_v2()
nova_client = Client(**credentials)
servers_usage(hypervisors)
print "\n"
hypervisors_usage(hypervisors)
print "\n"
cpu_layout(hypervisors)
