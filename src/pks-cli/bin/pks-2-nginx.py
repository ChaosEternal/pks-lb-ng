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

def gen_index(cls):
    header = """
<html><head><link rel="stylesheet" media="screen" href="/application.css">
</head><body><div class="container">
<nav class="site-header">
<a class="logo float-left" href="/" id="pivotal_cf_logo">
<center><div class="operations-manager-logo">Pivotal Container Service </div></center>
</a>
</nav>
<section class="content-container twelve columns" style="position: absolute; top: 80px; bottom: 0px;">
<div class="page-content nine columns">
<section class="dashboard">
<div class="scrolling-products">
<ul class="product-list nav nobullets">
</ul>
<script>
  $(function() {
    var availableProductsFixedFooter = $('#available-products-fixed-footer').detach();
    $('body').append(availableProductsFixedFooter);
  });
</script>
</div>
</section>
<section class="dashboard">
<header class="page-header">
<h2 id="main-page-marker">Kubernetes Clusters</h2>
</header>
<div class="infrastructure">
"""
    footer = """
</div>
</section>
</div>
</section>
</div>
</body></html>
"""
    l = ""
    for i in cls:
        if i["last_action"] == "CREATE":
            if i["last_action_state"] != "succeeded":
                continue
        if i["last_action"] not in ["CREATE", "UPDATE"]:
            continue
        tile = """
<div class="tile-wrapper">
<a data-progress="100" data-stemcell-present="true" id="show-pivotal-container-service-configure-action" class="configure tile added" href="https://dash.{cls_url}:18443/"><div class="product-icon">
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHYAAABuCAMAAADF/BfVAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAMAUExURQAAAACtnQCe3wCFcwBlrACGdACJcgBlqwCHdACGcwCGcwCwngCHcwCf3wCKhQCThgB6hgCGcwB3iwCY2QCHdwCGcwCIcgCHdACtmACEcwCd3gCGdACHcwCHcwCHcwCHdACHcwCHdACHcwCHdACHdACGdACGcwCHdACIdgCGcgCpmQCnlwCJdwCGcwCslgCY3QBmqgCJcwCPmACe3QBlqwCHcwBlrACGcwCHcwCGcwCHcwCJdQCHcwCxoABnrQBnqwCe3gBmrACHcwCvngBmrACHdACHdACe3gCqmQCsnACunwBkqQBipwCY2QCikQCFcQCh4QCvnwCvngCf3wCGcwCa1gCvnwCwnwCmlgCe3gCi5AB/aACZ2gCf4QCS0gBmrACDawCi7wBnrACY4ABmqgCHdACGcwCGcwBoqwBlrABmrABkrABlqwBmrACX2QBlrACunQCf3gBmrACe3gBlqwBlrQCHcwCf4ACqmgCh7ACZ2ABmrACyoACk5ACdiwC0pACtnQCunACungCBZwCdigCJeABmrACf3QBlrABmqwCrmwCY2ACQ0ACsmgCh4ACqmwCX1wCrmwCU1gChjwC0qACm5QB+awC4qACSfgCvoACa3AB/agCU1QCtnwB/awC3pwBYoACb0gBkqgCZwwCnlwB/TgCOzgCi8QCd1QCBXACZ2gCS0wCXiACX2ACPfACzpACHdACvnwCf3wBmrACxoQCwoACf3gCNegCDbwC3qACDYQCi7gCCbwCf4ACIdQCGcACzowCungCayACFbQCm5gCj8QCGcgBkqgCHdQCwoQCT1QCOfACh4gC1pQBiqQCBbQCRoAB+agB/bABcowCi4gCCXQBnrQCk9ACTgQCVgwCk4wC1pgCnlgB0uQCg5ACk5QCpmQC2pwCp6ACEZQCl+ACs6wCDcACjkgCQfgCh6ACi6wBfpgCsmwCR0wCRnwCZwgCNiwCj8wCj8ABWngCe1wCc0QCGbwCKggCYvACOkAB6ZgCFagCJywCAVQCSpACBxEyvdqgAAACwdFJOUwAvalSF+RjBvG7YJzrKCAUC5A0gFtZE3gwc9vW3sv01v2TPSifwyYR2LyAZU+kSChQS/v4zV7Wlil08rHAvehq3z8SYT2yRbYOip9drDzYh4H2Rp5d4+exL7cpRmYxHmfdprBZboJxPJqXEReLpXYnlnYLB+/V7YY81KZFoK2j3una1Oj75c6zuvVLCPNH9yqfhi/dBv9UvmfLd7OT0zNGE8sFvyqKz44b202or/U0rLC4BewAABrxJREFUaN7F2ndYE2ccB/CfWGyLNAQQQUAFlSGCLKsogrj33nvVbdU66q67du/d2r37z5tLLphAYlDQiCAVgkhAHgMCghO0ancvCcWEvO9LcnDh+2ceuM/zJnf3fe99D6B1Eoa6jfICJ2eQJ+LiGiZyJuoxADXENVzsNPVpV/QoASOdg3YYhqwTEuwENRzZxnOgwOhkH4SN7yohVZEnIsWts3DsKkSJzyDBzmFETY/uwrCRqJkMEwRuj5pNYK82YRFKnCwkGxJFhFd0EI4NFYeRRzzDSyjWB8BrBhkeJRKGdTN+0GklGU7w4Mu8MjWJzgJ0GUB0A57nBUe8yUok4yLoLECvrkQ4ZLDjdTzmrEZizNi+dJaDg8gjdrCcJm3SnJU0ZLgfnQXoHUqEHZkGeIyVySQWmSayuTm6Wf9H9x6k25b96pxjGlZinanU0RrT2RfLBtmL9t1vPVRzZh0AmE9jAXri4CfsVA8rNBJsZr8X+cdpNYXlmtGTN/ttqcbA4tgMzcfFVRdOayksQHAUP7bPkQvXSg0GvKu4UVyVbx6xG+kAI0P4sB1cUX4eCZbkKq5cyjPBbuRDJPBj1afz0y9dUZRg4ZIGmMJCV14sMsHFJNhgKOVgGjuYJ2uEL1QV38jF/sSswlB97QPKMZ7kzZrgvB1fZBDg3HcnCcNycF5v2HMMfxGzhtz9EcKwSH0IQDx1loSUcX0EYZG7qRfGEF3LVnSInbhgSspOOgvgN40MN7aiI+wGfx3DMCm76CxXD8PJ8A4/B1nvV/VGlctRbzrL3TTHkeE5DrEzVXqmMdOX01lubnXQUCLDXlCbRPazuz7R5zCWeW4inQV4oTpXweLgJLvZBTod0zQLouns/Lxz1QYFy59dNFevYmwTvxBEP2mJbKSxnKoNtnXczj52UWVljhzDMvIffowqPKUlsO2RloMvlSoM/NjvL/+ViYflaap/7jfC7rYPI1w55dm0op3s43cLLt/MLFdhYHnt1Xu3ThXe1xJYhLTGVrxRwoP9+qK0gIPLcbBcnnb1XtyfhSe0BNZUTumluTxGK+XCwdnl5QwGZtKKfour4GB30hOfOj/VcirtCHvxTMH1y9mVmbhvmqmv42DlIeKDZlWqRMaPbYD99dhTi8mqO3mHOFp0PJXlzRrhu8l7pzDYa0mVVTNvpzAsly8Bts/Fw2Vl8i17BWIfM37g4s+QsmVXs2xGEk8WYDQZTvG2XfyzYmXteLPgMZMMTzfDPfEsq/lIzJsFiF4YT4RNrSjyxbIyWeoSq+URx1gjLK+pwXYEMyXauCAUiGPPys6lo4DB/FmA5Ufji8qw8AbzKkUQgUUoKpg/C52OPKzFwqOtVikwLEKekbzZDksKHzxMK7JtRZfGP3H3IbAcvIov64oqlA9u1xc1LScXy+URNwKLkG9nvqwWKZV3bmfVWcMu1tMqXxmeRahHbDAv1tjkSuXvJ+vS4oksdJSxBBYFePJkG+D4WjmZfXRHbsoS1y6aZzn4xN8PysqcziJ0ouJkWluwp1qBDRKMlbGpZLarYCy7L/FTNYkNFoyV5EYAae0+HFrGxi8ls5IPAbrg1u5Du0AL2ZqZFNY0qZkc2ATt1nTFnsKCD5ZV1cV9F0tk2+E2DRJttoJobE88W39LiWbE0lmuFRt37qMw+8g0FmJXYtlfldzXluBFZwEGmTcNRuEWaKgsV/UDCCyXMA86y7WiDwrtDTzYhvMSyyLX8GZYEJP295plTeclnkXm2VrHDPKDJvBnjXtKFbfrcSxCIQMhQiMQy50eX9XiWaT+PHwfKxQL8+QEFh1XU55vW8o+RWZpT3z2sP1pLCMYK01uG1a6foQ97C0Km8SHlUrHj2iWzYor1BJYdrYfP1YqHbqOzjJp38xfgmdl7B7gy3JwPyrLLAWPsG62LKt5exK0gJVK1/ajsHLj7EKU0JTVsGPs345+WYpP/9Xk0ZrnUrErLFmZ7PUIB/beJ0hJWTaEznKznsT/WVbDvuDYiwYvEl3pmhg6a27FdLVEIzvoBw7GayMZXhxDZ7lJU2B6sWH2HD4vkcQsJsO7vegswOFpB/ryfGUmZg0Z3iyisy3KkGVEd2uy2LL4WpXl4P5EeNsEeF8lEAuwmgifH/9ZpmAsQL+1ePbM9ZtCshw8FMuezxaWBVg3vk1YgBHr6exoECjPPEtjtwM4B7ZkdW94g4CZ8BKOVen9F4GgESdvs2F1ureiQeiIN2+1YnP0c18DZ8RjowWrz3kHnBWv3Sb2ZqZO/7M3ODExiy9eL8iuZH4BJ2fIsn91Kctb51j/AbVN6wVdZtjaAAAAAElFTkSuQmCC">
</div>
<div class="tile-product-info">
<h4>{cls_name}</h4>
</div><div class="tile-product-info">
<p>{cls_url}</p>
</div>
<div class="progress-chart">

<div class="progress-indicator" style="width: 100%;"></div></div>
<div class="version" title="v1.1.0-build.311"> {cls_plan}/ {cls_size} nodes</div>
</a></div>

""".format(cls_name=i["name"],
           cls_url=i["parameters"]["kubernetes_master_host"],
           cls_plan=i["plan_name"],
           cls_size=i["parameters"]["kubernetes_worker_instances"]
)
        l += tile
    return header + l + footer
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
            ss = gen_index(cls)
            file(os.getenv("NGX_INDEX_FILE"), "w").write(ss)
            reloadngx()
            time.sleep(3)
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
