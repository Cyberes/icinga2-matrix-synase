# icinga2-matrix-synase



These are Icinga2 checks that I use to monitor my Matrix Synapse server. They're a little rough around the edges and you will likely need to adapt the code to fit your needs.



### Checks

`check_federation.py` uses two bots, one on your homeserver and the other on `matrix.org` to test federation between the two servers. Message send time is tracked.



`check_matrix_synapse.py` uses Grafana to check a bunch of metrics. Make sure you have set up the [official Grafana dashboard](https://matrix-org.github.io/synapse/latest/usage/administration/understanding_synapse_through_grafana_graphs.html). Make sure to review `checker/synapse_grafana.py` and add your worker jobs to the REST calls (for example, replace `federation-receiver|federation-sender|initialsync|synapse|synchrotron`).



`check_media_cdn.py` is a check I wrote to make sure that my media CDN is working properly. I use Cloudflare Workers to intercept the media endpoint and serve files from R2 so I need to make sure it's working as expected. This check uses a bot to upload a tiny image and read the request.



`check_monitor_bot.py` scrapes metrics from your [matrix-monitor-bot](https://github.com/turt2live/matrix-monitor-bot) instance.



`icinga2kuma.py` translates Icinga2 into something [uptime-Kuma](https://github.com/louislam/uptime-kuma) can understand. You should read the code to understand how it works (it's not that complicated), but basically it will return a 410 status code if Icinga2 reported a problem.

`http:/localhost:8081/host/[check hostname]?kuma=true&service=[service name]&exclude=[do not list these services]&ignore=[do not trigger a fail if these services fail]`

You can list `exclude` and `ignore` multiple times.

I've included a Systemd service to get you started.

You will need a password for the Icinga2 API. I just use the default `icingaweb2` user. See the file `/etc/icinga2/conf.d/api-users.conf`



### Notification Scripts

I really like these and they have worked well for me.

`matrix-host-notification.py` is to send Icinga2 host notifications to a Matrix room.

`matrix-service-notification.py` is to send service notifications.

