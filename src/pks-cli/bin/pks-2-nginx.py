#!/usr/bin/python
import sys, os, json
import fcntl
from contextlib import contextmanager
import BaseHTTPServer
import SimpleHTTPServer, time


    
@contextmanager
def flockfn(filename):
    """ Locks FD before entering the context, always releasing the lock. """
    try:
        fd = os.open(filename, os.O_WRONLY|os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def pks_login():
    os.system("pks-login")

def pks_getclusters():
    cls_js = os.popen("pks clusters --json").read()
    cls = json.loads(cls_js)
    return cls

def get_worknodes(c):
    cuuid   = c["uuid"]
    hosts   = file("/etc/hosts").readlines()
    workers = [x.split(' ')[0] for x in hosts if x.find(cuuid)>-1 and x.find("worker") > -1 ]
    return workers
    

def gen_ngx(cls):
    l = ""
    for i in cls:
        if i["last_action"] == "CREATE":
            if i["last_action_state"] != "succeeded":
                continue
        if i["last_action"] not in ["CREATE", "UPDATE"]:
            continue
        api = """upstream {cls_name} {{
        server {cls_m_ip}:8443;
    }}
    server {{
        client_max_body_size 10G;
        listen       8080 ;
        server_name  {cls_name};
        location / {{
            proxy_set_header Host $host;
            proxy_set_header X-HTTPS-Protocol $ssl_protocol;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Connection Upgrade;
            proxy_set_header Upgrade $http_upgrade;
            proxy_http_version 1.1;
            proxy_pass https://{cls_name};
        }}

        error_page 404 /404.html;
            location = /40x.html {{
        }}
    }}
    """.format(cls_name=i["parameters"]["kubernetes_master_host"], cls_m_ip=i["kubernetes_master_ips"][0])
        l += api + "\n"
        workers = get_worknodes(i)
        cls_workers_ssl = "\n".join(["server %s:30443 ;"%x for x in workers])
        cls_dash_ssl = "\n".join(["server %s:31443 ;"%x for x in workers])
        cls_workers = "\n".join(["server %s:30080 ;"%x for x in workers])
        ingress = """upstream worker-ssl.{cls_name} {{
        {cls_dash_ssl}
    }}
    upstream worker.{cls_name} {{
        {cls_workers}
    }}
    server {{
        client_max_body_size 10G;
        listen       8080 ;
        server_name  ~^(?<hostpart>.*)\\.{cls_name_escaped}$;
        location / {{
            proxy_set_header Host $hostpart;
            proxy_set_header X-HTTPS-Protocol $ssl_protocol;
            proxy_set_header X-Forwarded-Proto https;
            proxy_pass http://worker.{cls_name};
        }}

        error_page 404 /404.html;
            location = /40x.html {{
        }}
    }}
    server {{
        client_max_body_size 10G;
        listen       8443 ;
        server_name  ~^(?<hostpart>.*)\\.{cls_name_escaped}$;
        location / {{
            proxy_set_header Host $hostpart;
            proxy_set_header X-HTTPS-Protocol $ssl_protocol;
            proxy_set_header X-Forwarded-Proto https;
            proxy_pass https://worker-ssl.{cls_name};
        }}

        error_page 404 /404.html;
            location = /40x.html {{
        }}
    }}
""".format(cls_name=i["parameters"]["kubernetes_master_host"], cls_dash_ssl=cls_dash_ssl, cls_workers=cls_workers, cls_name_escaped=i["parameters"]["kubernetes_master_host"].replace(".", "\\."))
        l += ingress + "\n"
    return l

def find_domain_in_cls(d, cls):
    domainmatch = lambda a, b: len(a) - a.rfind(b) == len(b)
    return any(domainmatch(d, x["parameters"]["kubernetes_master_host"]) for x in cls)

def reloadngx():
    os.system("reload_ngx")

class PKSHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "PksHTTP/0.1"
    def r404(self, d):
        self.send_error(404, "The cluster: %s does not exists!"%d)
    def r504(self):
        self.send_error(504, "Please retry")
    def do_GET(self):
        d = self.server.server_name
        d = self.headers.get("Host", "localhost")
        with flockfn(os.getenv("LOCKFILE_PATH")):
            pks_login()
            cls = pks_getclusters()
            if not find_domain_in_cls(d, cls):
                return self.r404(d)
            r = gen_ngx(cls)
            file(os.getenv("NGX_CONF_FILE"), "w").write(r)
            reloadngx()
            time.sleep(30)
            return self.r504()
                

def test(HandlerClass = PKSHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer, protocol="HTTP/1.1"):

    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 8000
    server_address = ('127.0.0.1', port)

    HandlerClass.protocol_version = protocol
    httpd = ServerClass(server_address, HandlerClass)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


    
if __name__ == "__main__":
    test()
