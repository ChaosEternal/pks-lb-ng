#!/usr/bin/python
import sys, os, json
cls_js = os.popen("pks clusters --json").read()
cls = json.loads(cls_js)
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
    print(a)
