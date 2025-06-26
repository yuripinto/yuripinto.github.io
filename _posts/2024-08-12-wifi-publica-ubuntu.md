---
layout: post
title:  "Wifi Pública no Ubuntu"
date:   2024-08-12 11:40:00 -0300
categories: linux
permalink: wifi-publica-ubuntu
---

Desde que mudei meu sistema operacional para Ubuntu, abandonando meus longos anos de uso de MacBooks, redescobri algumas das limitações das famosas distros. Uma que encontrei hoje no Ubuntu é a dificuldade de se conectar a redes Wi-Fi públicas e abertas, com hotspots que exigem nome de usuário e senha, normalmente encontrados em hotéis e pousadas.

O Ubuntu não redireciona automaticamente para a página do hotspot que libera a conexão no roteador. A solução não é óbvia, mas é simples:

No terminal, digite `route -n`

Identifique o IP do gateway da conexão pública e acesse esse endereço pelo navegador

Coisa simples que já poderia vir integrada, né?