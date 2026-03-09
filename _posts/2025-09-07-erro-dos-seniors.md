---
layout: modern-post
title: "O erro dos sêniors"
date: 2025-09-07
permalink: "erro-dos-seniors"
image: /assets/covers/erro-dos-seniors.png
tags: [arquitetura, engenharia-de-software, team-topologies, times]
---

Eu sou complemente apaixonado por programação. Sempre gostei e ainda sinto o prazer de abrir um editor e escrever linhas de código, principalmente se for para resolver problemas da vida real. Mas essa não é a realidade da maioria dos desenvolvedores sêniores e especialistas que conheci durante esses anos trabalhando com tecnologia.

<!--more-->

Acredito que o motivo seja histórico: longos ciclos de projeto, com tecnologias monótonas, legadas, verbosas, em ambientes que valorizam velocidade e não qualidade, principalmente por falta de conhecimento técnico das camadas de liderança. Problemas em devops, observabilidade, e alta dependências entre times agravam a situação pros desenvolvedores mais experientes.

Dado esse contexto, para muitos, o sonho é abandonar o dia a dia de entregas, até mesmo técnico de vez. Em ambientes que em a “carreira em Y” se distancia das entregas de valor para o cliente, esses desenvolvedores migram muita das vezes para estruturas de arquiteturas, compliance, estruturais, entre outros que teoricamente recebem menos pressões corporativas.

O problema é que, na maioria das empresas, esses times criam processos e regras para as equipes de desenvolvimento, gerando dependências e processos manuais que tiram a autonomia dessas equipes. É um tanto paradoxal e vai contra o que as abordagens modernas de times prega: times cada vez mais autônomos.

Por isso acredito que cada vez mais devemos ir para os modelos de plataforma: ao contrário desses times criarem dependências, processos de aprovação - criem regras automatizadas em esteiras como ci/cd. Não faz sentido pedir pra alguém fora da equipe criar um banco de dados, um pod, ou uma alteração de schema manualmente. Se há uma regra, que essa seja automatizada e disponibilizada como software. Se a alteração feita pelos devs ferir essa regra, que seja bloqueada na esteira e tenha uma orientação de como deve ser feito. Assim podemos dar maior autonomia pros times, e deixar os especialistas projetando a melhor forma que os times devem trabalhar.