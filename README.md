Small websocket server for my home activity dashboard. uses a django backend, but manually making to check for new rows.

This isn't the best, and there's a lot to be desired, but this is to make my router have less of a bad time due to a bunch of polling that's happening right now

Default websocket port is 8811. It's wrapped behind my nginx/varnish setup for SSL

Symlinks are for the docker container, and don't actually exist on the host machine. But allows mounting it for dev work