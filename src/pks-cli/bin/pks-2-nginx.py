#!/usr/bin/python
import sys, os, json
import fcntl
from contextlib import contextmanager
import BaseHTTPServer
import SimpleHTTPServer


    
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

def gen_ngx(cls):
    l = ""
    for i in cls:
        if i["last_action_state"] != "succeeded":
            continue
        if i["last_action"] != "CREATE":
            continue
        a = """upstream {cls_name} {{
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
            proxy_pass https://{cls_name};
        }}

        error_page 404 /404.html;
            location = /40x.html {{
        }}
    }}
    """.format(cls_name=i["parameters"]["kubernetes_master_host"], cls_m_ip=i["kubernetes_master_ips"][0])
        l.append(a)
        l.append("\n")
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
        self,send_error(504, "Please retry")
    def do_GET(request):
        d = self.server.server_name
        with flockfn(os.getenv("LOCKFILE_PATH")):
            pks_login()
            cls = pks_getclusters()
            if not find_domain_cls(d, cls):
                return self.r404()
            r = gen_ngx(cls)
            file(os.getenv("NGX_CONF_FILE"), "w").write(r)
            reloadngx()
            return self.r504()
                

def test(HandlerClass = PKSHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    SimpleHTTPServer.test(HandlerClass, ServerClass)

if __name__ == "__main__":
    return test()
