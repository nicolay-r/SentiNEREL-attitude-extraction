## RuSentNE Sentiment Attitude Extraction Studies

![](https://img.shields.io/badge/Python-3.6-brightgreen.svg)
![](https://img.shields.io/badge/AREkit-0.23.0-orange.svg)

This repository represents studies related to sentiment attitude extraction, provided for 
sentiment relations of the [NEREL-based dataset](https://github.com/nerel-ds/nerel), dubbed as **SentiNEREL**.

The following spreadsheet represents ML-models benchmark evaluation results
obtained for the sentiment attitude relation extraction:

> [Leaderboard Google Spreadsheet](https://docs.google.com/spreadsheets/d/1o4VVZZNraO_-dr-WnGU8LM2aEjTp8KjZhFmTab5e5DM/edit?usp=sharing)

Powered by [AREkit-0.23.0](https://github.com/nicolay-r/AREkit) framework, based on the tutorial:
[Binding a custom annotated collection for Relation Extraction](https://nicolay-r.github.io/blog/articles/2022-08/arekit-collection-bind).

## Contents

* [Installation](#installation)
* [Download Finetuned Models](#download-finetuned-models)
* [Serialize SentiNEREL](#serialize-collection)
* [Frameworks](#frameworks)
    * [AREnets](framework/arenets) directory
    * [OpenNRE](framework/opennre) directory
    * [DeepPavlov](framework/deeppavlov) directory
    * [Hitachi-graph-based](framework/hitachi_graph) directory
* [Pretrained States](#pretrained-states)
* [Sponsors](#sponsors)

## Installation

```python
pip install -r dependencies.txt
```

> **NOTE:** some [frameworks](#frameworks) may require extra packages.

## Collection Serialization

* [arekit](tutorial/serialize.md) -- follow this tutorial to perform data serialization 
for `arenets`, `opennre`, and `deeppavlov` frameworks.

## Frameworks
   
* [opennre](framework/opennre/) -- based on OpenNRE toolkit (BERT-based models).
* [arenets](framework/arenets/) -- based on AREkit, tensorflow-based module 
for neural network training/finetunning/inferring.
* [deeppavlov](framework/deeppavlov/) `[legacy]` -- based on DeepPavlov framework (BERT-based models).
* [hittachi-graph-based](framework/hitachi_graph/) -- provides implementation of the graph-based 
approaches over transformers.

## Pretrained states
* [OpenNRE states](framework/opennre/)

### Sponsors

<p align="left">
    <img src="data/images/logo_msu.png"/>
</p>