---
layout: post
title: "Team Topologies"
date: 2025-08-24
tags: [arquitetura, engenharia-de-software, team-topologies, ddd, times, modernização]
---

Em uma conversa recente com um CTO, discutindo a modernização de um legado monolítico complexo em que ele e seu time atuam, ele comentou bastante sobre como os conceitos do livro *Team Topologies* fundamentaram o plano que eles montaram. Depois de fazer meu trabalho de casa (ler o livro e várias resenhas), fiquei com muita vontade de compartilhar minhas impressões.

*Team Topologies* é um livro que aplica e operacionaliza a lei de Conway, explorando como as estruturas de times afetam diretamente os resultados das empresas, em especial no desenho dos times de tecnologia, e como falhas nesse design podem ser danosas. Além disso, o livro é repleto de exemplos, cases e referências, sendo muito rico em insights e conexões com situações reais. Vejo uma ligação direta com o *Domain-Driven Design* de Eric Evans: enquanto Evans fala sobre design de software para remover silos entre negócio e tecnologia, *Team Topologies* mostra como alinhar a estrutura dos times para reduzir fricções organizacionais e reforçar esse alinhamento. Os autores reforçam a limitação da carga cognitiva como o pilar central para definir a divisão das estruturas organizacionais.

Segundo os autores, existem quatro tipos de times e três modos principais de interação entre eles, e que sair desses padrões pode ser nocivo para a organização:

**Stream-aligned**
Times responsáveis por um fluxo de valor claro, entregando diretamente ao cliente, com foco ponta a ponta.

**Plataforma**
Criam serviços que aceleram os times stream-aligned, removendo complexidades.

**Enabling**
Ajudam outros times com dicas, orientações e conhecimentos específicos. Atuam de forma temporária com cada time, mas são uma unidade permanente na organização.

**Subsistemas complexos**
Lidam com componentes de alta complexidade e exigem conhecimento muito específico. Exemplos incluem times de modelos de recomendação com IA ou de desenvolvimento em camadas próximas ao hardware.

| ![image](/assets/team-topologies/team-topologies-teams.webp) |
|:--:|
| *Fonte: [https://teamtopologies.com/key-concepts](https://teamtopologies.com/key-concepts)* |

E suas interações:

**Colaboração**
Trabalham em conjunto para descobrir ou definir tópicos (APIs, tecnologias, etc.).

**X-as-a-Service**
Um time provê um serviço que outro consome, com pouca necessidade de colaboração, a partir de definições claras e bem estabelecidas.

**Facilitação**
Um time ajuda e orienta o outro.


| ![image](/assets/team-topologies/team-topologies-interactions.webp) |
|:--:|
| *Fonte: [https://teamtopologies.com/key-concepts](https://teamtopologies.com/key-concepts)* |

A força de limitar-se a essas categorias é que isso ajuda a identificar problemas organizacionais e propor melhorias, especialmente em contextos de modernização, otimização ou fusões de estruturas.

É uma leitura essencial para profissionais de tecnologia em qualquer nível, mas especialmente valiosa para líderes e arquitetos de soluções que buscam transformar suas organizações.