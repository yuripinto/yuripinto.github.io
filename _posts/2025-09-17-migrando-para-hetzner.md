---
layout: modern-post
title: "Migrando do Heroku para o Hetzner"
date: 2025-09-17
permalink: "migrando-heroku-para-hetzner"
tags: [cloud]
published: false
---

Apesar de ter estudado, feito vários projetos e tirado várias certificações, minha experiência com a AWS não chega não perto da fluidez que é utilizar o Heroku. E claro, eu entendo algumas capacidades incríveis que a AWS fez que nenhum outro cloud provider tem, mas ainda sim, em termos do Devex, é difícil superar o quão simples e quão rápido é subir um Dyno e alguns addons no Heroku. Mas não tem almoço grátis, né?

<!--more-->

Eu tenho alguns pequenos projetos pessoais, em geral mini monolitos, que são aplicações que eu utilizo pro meu dia a dia, para estudos ou demonstrações de capacidades técnicas que eu gostaria de manter online.

Na média, um pequeno projeto no Heroku de CRUD básico custa pra mim em torno de $12/mês, incluindo $7 para 1 dyno básico (1 vCPU e 512 MB RAM) e 1 postgresql (0 RAM, 1GB de storage e 20 conexões). Se adicionar mais um dyno pra tentar consumir melhor as conexões do postgresql e ter um mínimo de HA, esse custo vai pra $19, que dá algo em torno de R$100, na conversão de hoje (dólar a R$ 5.3), sem contar os impostos adicionais (algo em torno de 3.5%). Quando eu tentei explorar esses custos direto na AWS, eu vi que o RDS mais simples, em us-east-1 (região mais barata), já saia de cara por $12/mês, justamente o custo do meu dyno + postgresql simples (sem contar o custo de manter essa infraestrutura). Pelo o que eu já vi no Heroku, entendo que eles conseguem oferecer esse postgresql mais barato porque no fim das contas eles estão provisionando um grande RDS, com vários schemas e users, e eles ganham na escala (que eu individualmente não tenho).

Porém olhando as opções de mercado, para providers mais simples, temos:
1. Digital Ocean oferecendo por $4/mês VM com 1 vCPU, 512 MB e 500 GB de file transfer, quase a metade do custo de um dyno Heroku
2. Hetzner oferecendo por $4.99/mês uma VM com 2 vCPU, 2GB RAM, 40 GB storage e 1 TB de tráfego, diferença gritante em relação todas as outras opções! Convertendo daria algo em torno de R$27 por app, quase 4x mais barato que o Heroku, isso sem imaginar que eu poderia ter mais de um app rodando nessa VM.

Hoje eu tenho 4 apps rodando no Heroku, cada um usando apenas 1 dyno, o que me custa em torno de $47/mês (R$250). Pensando em infraestrutura, e sem contar os custos pequenos que tenho de domínio, manter essa infraestrutura é bem barata, porém não tenho resiliência e não consigo escalar usuários. Mas o pior problema não é esse: se eu quiser criar mais projetos, eu tenho que pagar um custo alto pra isso. Se eu tiver 10 projetos onlines no Heroku, eu pagaria em torno de mil reais! Se eu tiver cada VM de $4.99 no Hetzner, cada uma rodando duas instâncias de apps, eu precisaria ter apenas 5 VM x $4.99 = ~133 reais!

Será que alguma conta está errada? Não é possível!