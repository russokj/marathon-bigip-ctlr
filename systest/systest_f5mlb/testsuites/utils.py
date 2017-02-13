"""Helper functions for orchestration tests."""


import copy
import re
import time

from pytest import symbols


REGISTRY = "docker-registry.pdbld.f5net.com"

DEFAULT_BIGIP_PASSWORD = "admin"
DEFAULT_BIGIP_USERNAME = "admin"

DEFAULT_DEPLOY_TIMEOUT = 6 * 60

DEFAULT_F5MLB_CPUS = 0.1
DEFAULT_F5MLB_MEM = 32
# FIXME(kenr): If we want to make general use of a second bigip in k8s, we
#              need to remove hard-coded use of this in the functions below.
DEFAULT_F5MLB_BIND_ADDR = symbols.bigip_ext_ip
BIGIP2_F5MLB_BIND_ADDR = getattr(symbols, 'bigip2_ext_ip', None)
DEFAULT_F5MLB_MODE = "http"
DEFAULT_F5MLB_NAME = "test-bigip-controller"
BIGIP2_F5MLB_NAME = "test-bigip-controller2"
DEFAULT_F5MLB_PARTITION = "test"
DEFAULT_F5MLB_PORT = 8080
DEFAULT_F5MLB_LB_ALGORITHM = "round-robin"
if symbols.orchestration == "marathon":
    DEFAULT_F5MLB_WAIT = 5
elif symbols.orchestration == "k8s":
    DEFAULT_F5MLB_WAIT = 20
DEFAULT_F5MLB_VERIFY_INTERVAL = 2
DEFAULT_F5MLB_NAMESPACE = "default"

DEFAULT_SVC_CPUS = 0.1
DEFAULT_SVC_HEALTH_CHECKS_HTTP = [
    {
        'path': "/",
        'protocol': "HTTP",
        'max_consecutive_failures': 3,
        'port_index': 0,
        'interval_seconds': 5,
        'grace_period_seconds': 10,
        'timeout_seconds': 5
    }
]
DEFAULT_SVC_HEALTH_CHECKS_TCP = [
    {
        'protocol': "TCP",
        'max_consecutive_failures': 3,
        'port_index': 0,
        'interval_seconds': 5,
        'grace_period_seconds': 10,
        'timeout_seconds': 5
    }
]
DEFAULT_SVC_INSTANCES = 1
DEFAULT_SVC_MEM = 32
DEFAULT_SVC_SSL_PROFILE = "Common/clientssl"
DEFAULT_SVC_PORT = 80

DEFAULT_BIGIP_MGMT_IP = symbols.bigip_mgmt_ip
DEFAULT_BIGIP2_MGMT_IP = getattr(symbols, 'bigip2_mgmt_ip', None)

if symbols.orchestration == "marathon":
    DEFAULT_F5MLB_CONFIG = {
        "MARATHON_URL": symbols.marathon_url,
        "F5_CC_SYSLOG_SOCKET": "/dev/null",
        "F5_CC_PARTITIONS": DEFAULT_F5MLB_PARTITION,
        "F5_CC_BIGIP_HOSTNAME": DEFAULT_BIGIP_MGMT_IP,
        "F5_CC_BIGIP_USERNAME": DEFAULT_BIGIP_USERNAME,
        "F5_CC_BIGIP_PASSWORD": DEFAULT_BIGIP_PASSWORD,
        "F5_CC_VERIFY_INTERVAL": str(DEFAULT_F5MLB_VERIFY_INTERVAL)
    }
    BIGIP2_F5MLB_CONFIG = copy.deepcopy(DEFAULT_F5MLB_CONFIG)
    BIGIP2_F5MLB_CONFIG['F5_CC_BIGIP_HOSTNAME'] = DEFAULT_BIGIP2_MGMT_IP
elif symbols.orchestration == "k8s":
    DEFAULT_F5MLB_CONFIG = {
        'cmd': "/app/bin/k8s-bigip-ctlr",
        'args': [
            "--bigip-partition", DEFAULT_F5MLB_PARTITION,
            "--bigip-url", DEFAULT_BIGIP_MGMT_IP,
            "--bigip-username", DEFAULT_BIGIP_USERNAME,
            "--bigip-password", DEFAULT_BIGIP_PASSWORD,
            "--verify-interval", str(DEFAULT_F5MLB_VERIFY_INTERVAL),
            "--namespace", DEFAULT_F5MLB_NAMESPACE
        ]
    }
    BIGIP2_F5MLB_CONFIG = copy.deepcopy(DEFAULT_F5MLB_CONFIG)
    BIGIP2_F5MLB_CONFIG['args'][3] = DEFAULT_BIGIP2_MGMT_IP

if symbols.orchestration == "marathon":
    DEFAULT_SVC_CONFIG = {
        'F5_PARTITION': DEFAULT_F5MLB_PARTITION,
        'F5_0_BIND_ADDR': DEFAULT_F5MLB_BIND_ADDR,
        'F5_0_PORT': DEFAULT_F5MLB_PORT,
        'F5_0_MODE': DEFAULT_F5MLB_MODE,
        'F5_0_BALANCE': DEFAULT_F5MLB_LB_ALGORITHM,
    }
    BIGIP2_SVC_CONFIG = copy.deepcopy(DEFAULT_SVC_CONFIG)
    BIGIP2_SVC_CONFIG['F5_0_BIND_ADDR'] = BIGIP2_F5MLB_BIND_ADDR
elif symbols.orchestration == "k8s":
    DEFAULT_SVC_CONFIG = {
        'name': "x",
        'labels': {'f5type': "virtual-server"},
        'data': {
            'data': {
                'virtualServer': {
                    'backend': {
                        'serviceName': "x",
                        'servicePort': DEFAULT_SVC_PORT,
                        'healthMonitors': [{
                            'send': "GET / HTTP/1.0\\r\\n\\r\\n",
                            'interval': 25,
                            'timeout': 20,
                            'protocol': "http"
                            }
                        ]
                    },
                    'frontend': {
                        'partition': DEFAULT_F5MLB_PARTITION,
                        'mode': DEFAULT_F5MLB_MODE,
                        'balance': DEFAULT_F5MLB_LB_ALGORITHM,
                        'virtualAddress': {
                            'bindAddr': DEFAULT_F5MLB_BIND_ADDR,
                            'port': DEFAULT_F5MLB_PORT
                        }
                    }
                }
            },
            'schema': 'f5schemadb://bigip-virtual-server_v0.1.2.json'
        }
    }
    BIGIP2_SVC_CONFIG = copy.deepcopy(DEFAULT_SVC_CONFIG)
    BIGIP2_SVC_CONFIG['data']['data']['virtualServer']['frontend'][
            'virtualAddress']['bindAddr'] = BIGIP2_F5MLB_BIND_ADDR


def create_managed_northsouth_service(
        orchestration, id="test-svc",
        cpus=DEFAULT_SVC_CPUS,
        mem=DEFAULT_SVC_MEM,
        labels={},
        timeout=DEFAULT_DEPLOY_TIMEOUT,
        health_checks=DEFAULT_SVC_HEALTH_CHECKS_HTTP,
        num_instances=DEFAULT_SVC_INSTANCES,
        config=DEFAULT_SVC_CONFIG,
        wait_for_deploy=True):
    """Create a microservice with bigip-controller decorations."""
    # - note that we have to have to make a copy of the "labels" dictionary
    #   before we try to mutate it, otherwise the mutated version will persist
    #   through subsequent calls to "create_managed_service"
    # - we found this issue in the iapp test, where the next test that ran
    #   after the iapp test had its labels set to a combination of the iapp
    #   test's labels plus the non-iapp test's labels
    # - this was a Python scoping surprise to me!
    _lbls = copy.deepcopy(labels)
    if symbols.orchestration == "marathon":
        _lbls.update(config)
    if symbols.orchestration == "k8s":
        orchestration.namespace = "default"
    svc = orchestration.app.create(
        id=id,
        cpus=cpus,
        mem=mem,
        timeout=timeout,
        container_img="%s/systest-common/test-nginx" % REGISTRY,
        labels=_lbls,
        container_port_mappings=[
            {
                'container_port': DEFAULT_SVC_PORT,
                'host_port': 0,
                'service_port': 0,
                'protocol': "tcp"
            }
        ],
        container_force_pull_image=True,
        health_checks=health_checks,
        num_instances=num_instances,
        wait_for_deploy=wait_for_deploy
    )
    if symbols.orchestration == "k8s":
        config['name'] = "%s-map" % id
        config['data']['data']['virtualServer']['backend']['serviceName'] = id
        orchestration.app.create_configmap(config)
    return svc


def unmanage_northsouth_service(orchestration, svc):
    """Remove bigip-controller decorations from a managed microservice."""
    if symbols.orchestration == "marathon":
        svc.labels = {}
        svc.update()
    if symbols.orchestration == "k8s":
        orchestration.namespace = "default"
        orchestration.app.delete_configmap("%s-map" % svc.id)


def create_bigip_controller(
        orchestration, id=DEFAULT_F5MLB_NAME, cpus=DEFAULT_F5MLB_CPUS,
        mem=DEFAULT_F5MLB_MEM, timeout=DEFAULT_DEPLOY_TIMEOUT,
        config=DEFAULT_F5MLB_CONFIG, wait_for_deploy=True):
    """Create a bigip-controller microservice."""
    if symbols.orchestration == "marathon":
        return orchestration.app.create(
            id=id,
            cpus=cpus,
            mem=mem,
            timeout=timeout,
            container_img=symbols.bigip_controller_img,
            container_force_pull_image=True,
            env=config,
            wait_for_deploy=wait_for_deploy
        )
    if symbols.orchestration == "k8s":
        orchestration.namespace = "kube-system"
        return orchestration.app.create(
            id=id,
            cpus=cpus,
            mem=mem,
            timeout=timeout,
            container_img=symbols.bigip_controller_img,
            container_force_pull_image=True,
            cmd=config['cmd'],
            args=config['args'],
            wait_for_deploy=wait_for_deploy
        )


def create_unmanaged_service(orchestration, id, labels={}):
    """Create a microservice with no bigip-controller decorations."""
    if symbols.orchestration == "k8s":
        orchestration.namespace = "default"
    return orchestration.app.create(
        id=id,
        cpus=DEFAULT_SVC_CPUS,
        mem=DEFAULT_SVC_MEM,
        timeout=DEFAULT_DEPLOY_TIMEOUT,
        container_img="%s/systest-common/test-nginx" % REGISTRY,
        labels=labels,
        container_port_mappings=[
            {
                'container_port': DEFAULT_SVC_PORT,
                'host_port': 0,
                'protocol': "tcp"
            }
        ],
        container_force_pull_image=True
    )


def get_backend_object_name(svc, port_idx=0):
    """Generate expected backend object name."""
    if symbols.orchestration == "marathon":
        return (
            "%s_%s_%s"
            % (
                svc.id.replace("/", ""),
                svc.labels['F5_%d_BIND_ADDR' % port_idx],
                str(svc.labels['F5_%d_PORT' % port_idx])
            )
        )
    if symbols.orchestration == "k8s":
        return (
            "%s_%s_%s" % (svc.id, svc.vs_bind_addr, svc.vs_port)
        )


def wait_for_bigip_controller(num_seconds=DEFAULT_F5MLB_WAIT):
    """Wait for bigip-controller to restore expected state (or not!)."""
    time.sleep(num_seconds)


def get_backend_objects(bigip, partition=DEFAULT_F5MLB_PARTITION):
    """Get the resources managed by BIG-IP."""
    ret = {}

    if not bigip.partition.exists(name=partition):
        return {}

    # - get list of virtual servers
    virtual_servers = bigip.virtual_servers.list(partition=partition)
    if virtual_servers:
        ret['virtual_servers'] = virtual_servers

    # - get list of virtual addresses
    virtual_addresses = bigip.virtual_addresses.list(partition=partition)
    if virtual_addresses:
        ret['virtual_addresses'] = virtual_addresses

    # - get list of pools
    pools = bigip.pools.list(partition=partition)
    if pools:
        ret['pools'] = pools

    # - get list of pool members
    pool_members = bigip.pool_members.list(partition=partition)
    if pool_members:
        ret['pool_members'] = pool_members

    # - get list of health monitors
    health_monitors = bigip.health_monitors.list(partition=partition)
    if health_monitors:
        ret['health_monitors'] = health_monitors

    # - get list of nodes
    nodes = bigip.nodes.list(partition=partition)
    if nodes:
        ret['nodes'] = nodes

    return ret


def get_backend_objects_exp(svc):
    """A dict of the expected backend resources."""
    instances = svc.instances.get()
    obj_name = get_backend_object_name(svc)
    if symbols.orchestration == "marathon":
        virtual_addr = svc.labels['F5_0_BIND_ADDR']
    elif symbols.orchestration == "k8s":
        virtual_addr = DEFAULT_F5MLB_BIND_ADDR
    ret = {
        'virtual_servers': [obj_name],
        'virtual_addresses': [virtual_addr],
        'health_monitors': [obj_name],
        'pools': [obj_name],
        'pool_members': [
            "%s:%d" % (instances[0].host, instances[0].ports[0])
        ],
        'nodes': [instances[0].host],
    }
    return ret


def wait_for_backend_objects(
        bigip, objs_exp, partition=DEFAULT_F5MLB_PARTITION, timeout=60):
    """Verify that the actual backend resources match what's expected."""
    interval = 2
    duration = 0
    while get_backend_objects(bigip) != objs_exp and duration <= timeout:
        time.sleep(interval)
        duration += interval
    assert get_backend_objects(bigip) == objs_exp


def verify_bigip_round_robin(ssh, svc, protocol=None, ipaddr=None, port=None):
    """Verify round-robin load balancing behavior."""
    # - bigip round robin is not as predictable as we would like (ie. you
    #   can't be sure that two consecutive requests will be sent to two
    #   separate pool members - but if you send enough requests, the responses
    #   will average out to something like what you expected).
    svc_url = _get_svc_url(svc, protocol, ipaddr, port)
    num_members = svc.instances.count()
    num_requests = num_members * 10
    min_res_per_member = 2

    # - send the target number of requests and collect the responses
    act_responses = {}
    curl_cmd = "curl -s -k %s" % svc_url
    ptn = re.compile("^Hello from .+ :0\)$")
    for i in range(num_requests):
        res = ssh.run(symbols.bastion, curl_cmd)
        # - verify response looks good
        assert re.match(ptn, res)
        if res not in act_responses:
            act_responses[res] = 1
        else:
            act_responses[res] += 1

    # - verify we got at least 2 responses from each member
    for k, v in act_responses.iteritems():
        assert v >= min_res_per_member


def _get_svc_url(svc, protocol=None, ipaddr=None, port=None):
    if symbols.orchestration == "marathon":
        return _get_svc_url_marathon(svc, protocol, ipaddr, port)
    elif symbols.orchestration == "k8s":
        return _get_svc_url_k8s(svc, protocol, ipaddr, port)


def _get_svc_url_marathon(svc, protocol=None, ipaddr=None, port=None):
    if protocol is None:
        if 'F5_0_SSL_PROFILE' in svc.labels:
            protocol = "https"
        else:
            protocol = "http"
    if ipaddr is None:
        if 'F5_0_BIND_ADDR' in svc.labels:
            ipaddr = svc.labels['F5_0_BIND_ADDR']
        else:
            ipaddr = DEFAULT_F5MLB_BIND_ADDR
    if port is None:
        if 'F5_0_PORT' in svc.labels:
            port = svc.labels['F5_0_PORT']
        else:
            port = DEFAULT_F5MLB_PORT
    return "%s://%s:%s" % (protocol, ipaddr, port)


def _get_svc_url_k8s(svc, protocol=None, ipaddr=None, port=None):
    vs_config = svc.vs_config
    # - we can't just assume that virtualAddress will exist because the
    #   virtual server might have been configured by an iApp
    vs_addr = vs_config.get('frontend', {}).get('virtualAddress', {})
    if protocol is None:
        if 'sslProfile' in vs_config.get('frontend', {}):
            protocol = "https"
        else:
            protocol = "http"
    if ipaddr is None:
        if 'bindAddr' in vs_addr:
            ipaddr = vs_addr['bindAddr']
        else:
            ipaddr = DEFAULT_F5MLB_BIND_ADDR
    if port is None:
        if 'port' in vs_addr:
            port = vs_addr['port']
        else:
            port = DEFAULT_F5MLB_PORT
    return "%s://%s:%s" % (protocol, ipaddr, port)
