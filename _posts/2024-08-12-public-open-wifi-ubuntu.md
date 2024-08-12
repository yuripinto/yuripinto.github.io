---
layout: post
title:  "Public Open Wifi on Ubuntu"
date:   2024-08-12 11:40:00 -0300
categories: linux
permalink: public-open-wifi-ubuntu
---

Since I changed my OS to Ubuntu, abandoning my long years of using MacBooks, I have rediscovered some of the limitations of the famous distros. One that I found today in Ubuntu is the difficulty we have in connecting to Public Open Wifi, with hotpots that require a username and password, normally found in hotels and inns.

Ubuntu does not redirect to the hotpot page that allows your connection to be released on the router. The solution is not obvious, but it is simple:

1. At the command prompt, type `route -n`
2. Identify the IP of the public connection gateway and access this address through the browser

Simple thing that could already be built in, right?