

{0}------------------------------------------------

###### RESEARCH ARTICLE

# A network pharmacology-based approach to explore the therapeutic potential of *Sceletium tortuosum* in the treatment of neurodegenerative disorders

Yangwen Luo<sup>1</sup>, Luchen Shan<sup>1</sup>, Lipeng Xu<sup>1</sup>, Srinivas Patnala<sup>2</sup>, Isadore Kanfer<sup>2</sup>\*, Jiahao Li<sup>1</sup>, Pei Yu<sup>1</sup>\*, Xu Jun<sup>1</sup> ![ORCID icon](666e09182d4cd268646ea700ea60dcdf_img.jpg)\*

**1** College of Pharmacy, Jinan University, Guangzhou, China, **2** Faculty of Pharmacy, Rhodes University, Grahamstown, South Africa

¤ Current address: Leslie Dan Faculty of Pharmacy, University of Toronto, Toronto, Canada

\* [peiyu@jnu.edu.cn](mailto:peiyu@jnu.edu.cn) (PY); [xujun@jnu.edu.cn](mailto:xujun@jnu.edu.cn) (JX)

![Check for updates icon](4f4b52340aaccb1bcf733468dca9ee03_img.jpg)

Check for updates icon

###### OPEN ACCESS

**Citation:** Luo Y, Shan L, Xu L, Patnala S, Kanfer I, Li J, et al. (2022) A network pharmacology-based approach to explore the therapeutic potential of *Sceletium tortuosum* in the treatment of neurodegenerative disorders. PLoS ONE 17(8): e0273583. <https://doi.org/10.1371/journal.pone.0273583>

**Editor:** Oksana Lockr[id](https://orcid.org/0000-0001-6056-7381)ge, University of Nebraska Medical Center, UNITED STATES

**Received:** February 24, 2022

**Accepted:** August 10, 2022

**Published:** August 25, 2022

**Copyright:** © 2022 Luo et al. This is an open access article distributed under the terms of the [Creative Commons Attribution License](https://creativecommons.org/licenses/by/4.0/), which permits unrestricted use, distribution, and reproduction in any medium, provided the original author and source are credited.

**Data Availability Statement:** All relevant data are within the paper.

**Funding:** The author(s) received no specific funding for this work.

**Competing interests:** The authors have declared that no competing interests exist.

**Abbreviations:** SCT, *Sceletium tortuosum*; MPP<sup>+</sup>, 1-methyl-4-phenylpyridinium; AChE, Acetylcholinesterase; MAO, monoamine oxidase;

## Abstract

*Sceletium tortuosum* (SCT) has been utilized medicinally by indigenous Koi-San people purportedly for mood elevation. SCT extracts are reported to be neuroprotective and have efficacy in improving cognition. However, it is still unclear which of the pharmacological mechanisms of SCT contribute to the therapeutic potential for neurodegenerative disorders. Hence, this study investigated two aspects—firstly, the abilities of neuroprotective sub-fractions from SCT on scavenging radicals, inhibiting some usual targets relevant to Alzheimer's disease (AD) or Parkinson's disease (PD), and secondly utilizing the network pharmacology related methods to search probable mechanisms using Surflex-Dock program to show the key targets and corresponding SCT constituents. The results indicated sub-fractions from SCT could scavenge 2,2-diphenyl-1-picrylhydrazyl (DPPH) radical, inhibit acetylcholinesterase (AChE), monoamine oxidase type B (MAO-B) and N-methyl-D-aspartic acid receptor (NMDAR). Furthermore, the results of gene ontology and docking analyses indicated the key targets involved in the probable treatment of AD or PD might be AChE, MAO-B, NMDAR subunit2B (GluN2B-NMDAR), adenosine A<sub>2A</sub> receptor and cannabinoid receptor 2, and the corresponding constituents in *Sceletium tortuosum* might be N-trans-feruloyl-3-methyldopamine, dihydrojoubertiamine and other mesembrine type alkaloids. In summary, this study has provided new evidence for the therapeutic potential of SCT in the treatment of AD or PD, as well as the key targets and notable constituents in SCT. Therefore, we propose SCT could be a natural chemical resource for lead compounds in the treatment of neurodegenerative disorders.

## Introduction

*Sceletium tortuosum* (L.) *N.E. Br* (SCT), a South African herb, with a long history of use by Koi-San natives, is reported to have various pharmacological activities such as anti-depressant

{1}------------------------------------------------

NMDAR, N-methyl-D-aspartic acid receptor; AD, Alzheimer's disease; PD, Parkinson's disease; DPPH, 1,1-diphenyl-2-picrylhydrazyl; A2AR, adenosine A2A receptor; CB2R, cannabinoid receptor 2; KEGG, Kyoto Encyclopedia of Genes and Genomes.

[[1](#block-17-0)], anti-anxiety [[2](#block-17-0)], anti-epileptic [[3](#block-17-0)] and analgesic [[4](#block-17-0)] activities. Its extracts are reported to have shown efficacy in improving cognition [[5](#block-17-0), [6](#block-17-0)]. Cognition deficit is a predominantly general symptom of Alzheimer's disease (AD) and in some cases of Parkinson's diseases (PD)—hence it is postulated that neurodegenerative disorders that could be treated by compounds that possess neuroprotective effects [[7](#block-17-0)–[12](#block-18-0)]. Considering that there are certain neuroprotective constituents in SCT, which are reported to have the therapeutic potential in the treatment of neurodegenerative diseases, there is a need to investigate the probable mechanisms that contribute to the possible treatment of neurodegenerative disorders, especially in AD or PD with cognitive impairments.

“Network pharmacology” (NP) methods have been usually applied in this form of research to access primary mechanisms of certain traditional Chinese medicines formula according to their traditional indications [[13](#block-18-0)–[16](#block-18-0)]. Some studies have also used NP to explore the possible novel indications for complicated Chinese traditional medicines [[17](#block-18-0), [18](#block-18-0)]. Application of NP could be further understood based on the published report by Fang JS et al who proposed and deciphered mechanism of action for some of the most widely studied medicinal herbs used in the treatment of AD [[19](#block-18-0)].

Our previous study [[20](#block-18-0)] has showed the neuroprotective sub-fractions and possible neuroprotective constituents ([Fig 1](#block-2-0)) in the neuroprotective sub-fractions extracted from SCT. The petroleum ether and ethyl acetate fractions were confirmed to possess neuroprotective efficacy, been further separated by silica gel column to obtain sub-fractions tested by cell experiments. Furthermore, natural products generally consist of various and diverse active constituents depending on the extraction process [[21](#block-18-0)], which can lead to neuroprotective fractions that exert neuroprotective effect of SCT and probably caused due to multiple constituents. Thus, it makes such investigations laborious and difficult to decipher the elicited mechanisms. Hence, investigating the possibility of SCT extract for treating neurodegenerative disorders, as an integrated system as applied by traditional Chinese medicine, would provide insight by utilizing NP methods is a logical and scientific approach.

In this study, spectrophotometric assays were performed on SCT sub-fractions to assess neuroprotective action related efficacies based on the scavenging radicals, inhibiting acetylcholinesterase (AChE), monoamine oxidases (MAOs) and N-methyl-D-aspartic acid receptor (NMDAR). Subsequently, relevant NP methods and molecular docking were performed to understand the possible mechanisms that provide evidence to correlate the therapeutic potential of SCT in the treatment of AD or PD.

Furthermore, it is important to identify the key targets, and the corresponding constituents in neuroprotective sub-fractions involved in the probable treatment of AD or PD [[2](#block-17-0), [4](#block-17-0), [22](#block-18-0)–[33](#block-19-0)].

## Methods

### The neuroprotective sub-fractions from SCT and their identified constituents

Based on our previous study [[20](#block-18-0)], SCT plant powder was extracted with alcohol and which was further extracted with petroleum ether and ethyl acetate. The petroleum ether and ethyl acetate fractions were confirmed to possess neuroprotective efficacy on MPP<sup>+</sup>-injured N2a cells or L-glutamate-injured PC12 cells. The active fractions were further separated by silica gel column to obtain sub-fractions. The sub-fractions were also tested by cell experiments [[34](#block-19-0)–[36](#block-19-0)] to give four neuroprotective sub-fractions—P5, P6, E1 and E3 (“P” and “E” mean the sub-fractions of petroleum ether and ethyl acetate fractions respectively). The active sub-fractions were once again preliminarily identified the constituents that were separated and identified

{2}------------------------------------------------

![Chemical structures of 18 constituents of neuroprotective sub-fractions from SCT, arranged in a 5x3 grid. Each structure is accompanied by its name and retention time (tR) in minutes. Chemical structure of a bicyclic indole derivative Chemical structure of Zephycandidine 2 Chemical structure of 4'-O-demethyl-mesembrenone Chemical structure of Sceletium A4 Chemical structure of Mesembrine Chemical structure of Mesembrenone Chemical structure of Sceletone Chemical structure of Dihydrojoubertamine Chemical structure of 2-oxomesembrine Chemical structure of Δ⁷-N-demethyl-mesembrenone Chemical structure of 7,7a-dehydro-mesembrenone Chemical structure of Δ⁷-Mesembrenone Chemical structure of N-demethyl-N-formylmesembrenone Chemical structure of Delagoensine Chemical structure of 4-O-methylsceletone Chemical structure of 2-oxomesembranol Chemical structure of Dihydrobuphanamine acetate Chemical structure of N-trans-feruloyl-3-methyldopamine Chemical structure of N-Methyldihydrojoubertinamine Chemical structure of Egonie Chemical structure of Egonie](19147f50869a7b98fab606b9cab58e1f_img.jpg)

|                                                    |                                          |                                                 |                                                 |                                                        |                                                      |                                |
|----------------------------------------------------|------------------------------------------|-------------------------------------------------|-------------------------------------------------|--------------------------------------------------------|------------------------------------------------------|--------------------------------|
| <br>tR = 1.19 min                                  | <br>Zephycandidine 2<br>tR = 1.24 min    | <br>4'-O-demethyl-mesembrenone<br>tR = 1.44 min | <br>Sceletium A4<br>tR = 1.93 min               | <br>Mesembrine<br>tR = 2.11 min                        | <br>Mesembrenone<br>tR = 2.12 min                    | <br>Sceletone<br>tR = 2.67 min |
| <br>Dihydrojoubertamine<br>tR = 2.73 min           | <br>2-oxomesembrine<br>tR = 2.731 min    | <br>Δ⁷-N-demethyl-mesembrenone<br>tR = 2.97 min | <br>7,7a-dehydro-mesembrenone<br>tR = 3.28 min  | <br>Δ⁷-Mesembrenone<br>tR = 3.35 min                   | <br>N-demethyl-N-formylmesembrenone<br>tR = 3.50 min |                                |
| <br>Delagoensine<br>tR = 3.71 min                  | <br>4-O-methylsceletone<br>tR = 3.86 min | <br>2-oxomesembranol<br>tR = 4.03 min           | <br>Dihydrobuphanamine acetate<br>tR = 4.14 min | <br>N-trans-feruloyl-3-methyldopamine<br>tR = 4.22 min |                                                      |                                |
| <br>N-Methyldihydrojoubertinamine<br>tR = 4.97 min | <br>Egonie<br>tR = 5.26 min              | <br>Egonie<br>tR = 5.261 min                    |                                                 |                                                        |                                                      |                                |

Chemical structures of 18 constituents of neuroprotective sub-fractions from SCT, arranged in a 5x3 grid. Each structure is accompanied by its name and retention time (tR) in minutes. Chemical structure of a bicyclic indole derivative Chemical structure of Zephycandidine 2 Chemical structure of 4'-O-demethyl-mesembrenone Chemical structure of Sceletium A4 Chemical structure of Mesembrine Chemical structure of Mesembrenone Chemical structure of Sceletone Chemical structure of Dihydrojoubertamine Chemical structure of 2-oxomesembrine Chemical structure of Δ⁷-N-demethyl-mesembrenone Chemical structure of 7,7a-dehydro-mesembrenone Chemical structure of Δ⁷-Mesembrenone Chemical structure of N-demethyl-N-formylmesembrenone Chemical structure of Delagoensine Chemical structure of 4-O-methylsceletone Chemical structure of 2-oxomesembranol Chemical structure of Dihydrobuphanamine acetate Chemical structure of N-trans-feruloyl-3-methyldopamine Chemical structure of N-Methyldihydrojoubertinamine Chemical structure of Egonie Chemical structure of Egonie

**Fig 1. The constituents of neuroprotective sub-fractions from SCT in previous study.** (tR represents their retention time in UPLC).

<https://doi.org/10.1371/journal.pone.0273583.g001>

from SCT in the current study. The chemical structures of these constituents are depicted in Fig 1.

### DPPH scavenging assay

The ability of the neuroprotective sub-fractions from SCT to scavenge 2,2-diphenyl-1-picrylhydrazyl (DPPH) radical was tested in 96-well polystyrene microtiter plates (Corning<sup>®</sup>). The extraction and separation methods to obtain the neuroprotective sub-fractions were performed as described in the previous study [[20](#block-18-0)]. DPPH (TCI, Japan) was dissolved in methanol

{3}------------------------------------------------

to obtain a concentration of 100  $\mu\text{M}$ . The wells contained 100  $\mu\text{L}$  DPPH and then added 100  $\mu\text{L}$  of sub-fraction samples in different concentrations. Blank wells contained methanol in place of DPPH and control wells contained only methanol in place of samples. After shocking on a microoscillator, the plate was kept in the dark for 50 minutes. The absorbance was detected at a wavelength of 517 nm using a microplate reader (Bio-Tek Instruments Inc, USA). The clearance percent of DPPH was expressed as mean  $\pm$  SEM calculated by following formula:

$$\text{Clearance (\%)} = \frac{A_{\text{control}} - (A_{\text{sample}} - A_{\text{blank}})}{A_{\text{control}}} \times 100\%$$

### AChE inhibition assay

The experiment to test the AChE inhibiting ability of neuroprotective sub-fractions of SCT was performed as per procedure described by Ellman [[37](#block-19-0), [38](#block-19-0)]. 160  $\mu\text{L}$  of PBS (0.1 M pH = 8), 10  $\mu\text{L}$  of sample and 10  $\mu\text{L}$  of AChE (0.5 U/mL, Solarbio, Beijing) were mixed in 96 wells plate for 20 min at 4°C, and then the wells were added 10  $\mu\text{L}$  of 2,2'-dithiodibenzoic acid (10 mM, MedChemExpress) and 10  $\mu\text{L}$  of acetylthiocholine iodide (10 mM, Solarbio, Beijing) for another 30 min at 37°C. The absorbance was detected at a wavelength of 405 nm. Blank wells had PBS added in place of AChE and control wells had PBS added in place of samples.

### MAOs inhibition assay

The MAOs inhibition percent of neuroprotective sub-fractions from SCT was measured by following procedures described by Holt with some modifications [[39](#block-19-0)].

This study is got pass by Jinan University Laboratory Animal Ethical Committee. The IACUC issue number is 20220225–03. All studies related to animals were performed in accordance with the standards set forth in the eighth edition of Guide for the Care and Use of Laboratory animals, published by the National Academy of Sciences, the National Academies Press, Washington D.C (License number: SCXK(粤)2018-0002). We use Pentobarbital Sodium as anesthesia and reduce the pain of death in rats by excessive anaesthesia.

Female Sprague—Dawley rat (286 g) was killed by anesthetic, and its livers were dissected out, washed in ice-cold PBS (0.2 M, pH 7.6). Liver tissue (7 g) was homogenized 1:20 (w/v) in 0.3 M sucrose with a mechanical homogenizer. Following centrifugation at 1100g for 12 min, the supernatant was further centrifuged at 10 000g for 30 min to obtain a crude mitochondrial pellet, which was resuspended in 40 ml of PBS used as the source of MAOs.

40  $\mu\text{L}$  of MAOs and 40  $\mu\text{L}$  of samples were added in the wells for 20 min at 37°C and then the supplement of the enzyme substrate and chromogenic reagent were added for 60 min at 37°C. The enzyme substrate was tyramine (5 mM, Aladdin, Shanghai) and the chromogenic reagent was a mixture contained vanillic acid (5 mM, Shanghaiyuanye, China), 4-aminoantipyrine (1mM, Shanghaiyuanye, China), peroxidase (5 U/mL, Solarbio, Beijing) in PBS. The absorbance was detected at a wavelength of 490 nm. Blank wells had PBS added in place of tyramine and control wells had PBS added in place of samples.

The inhibition percentages of AChE and MAOs were expressed as mean  $\pm$  SEM calculated by following formula:

$$\text{Inhibition percent (\%)} = \frac{A_{\text{control}} - (A_{\text{sample}} - A_{\text{blank}})}{A_{\text{control}}} \times 100\%$$

#### Primary culture of rat hippocampal neurons

The hippocampus tissue was separated from Sprague-Dawley neonatal rat and placed in cold phosphate buffer saline under an asepsis condition, and then was digested with 0.25% trypsin

{4}------------------------------------------------

for 20 min at 37°C. After trypsinization, hippocampal neurons were suspended in DMEM (Gibco) containing 10% horse serum (Gibco) and cultured in polyethylenimine-coated coverslips at a density of 105/cm<sup>2</sup> for 4 h at 37°C. The medium was replaced with neurobasal medium (Gibco) containing B-27 supplement (Gibco) and L-glutamine (Gibco), and the cells were cultured at 37°C in a humidified environment of 95% air and 5% CO<sub>2</sub> for 7 days.

#### Whole cell patch clamp

To investigate the effect of two sub-fractions from SCT on the NMDAR mediated current, whole cell patch clamp was used to the record of NMDAR current by an amplifier (EPC-10, HEKA, Germany). Before recording, a negative pressure was exerted on the hippocampal neuron's surface through microelectrode and formed a GΩ seal resistance, then the membrane potential was kept in -70 mV. The hippocampal neurons were exposed to NMDA (100 μM), Glycine (10 μM) and samples in different concentrations or D-2-Amino-5-phosphonovaleric acid (D-AP5) (100 μM).

NMDA (100 μM) and Glycine (10 μM) were used to activate the NMDA current. D-AP5, a NMDAR inhibitor, was used as a positive control. The current signals were recorded by the amplifier under a Gap-free mode and stored in PatchMaster software (HEKA, Germany).

Recording was allowed to start at least 5 min after the rupture of patch membrane to ensure stabilization of the intracellular milieu. Neurons that showed unstable or large (more than ~ 50 pA) holding currents were rejected. The series resistance (< 15 MΩ) and membrane capacitance were compensated and checked regularly during the recording.

The inhibition percentage of NMDAR was calculated according to the formula:  $(1 - (I_{\text{NMDA}} + \text{Glycine} + \text{Compound} / I_{\text{NMDA}} + \text{Glycine})) \times 100\%$ . Data were expressed as mean ± S.E.M.

Extracellular fluid (pH 7.4) contained 140 mM NaCl, 4 mM KCl, 2 mM CaCl<sub>2</sub>•2H<sub>2</sub>O, 10 mM HEPES, 5 mM D-Glucose, 0.5 μM TTX, 10 μM NBQX, 10 μM Strychnine and 10 μM Bicuculline. Intracellular fluid (pH 7.2) contained 10 mM NaCl, 110 mM CsMeS, 2 mM MgCl<sub>2</sub>•6H<sub>2</sub>O, 10 mM HEPES, 10 mM EGTA, 2 mM Na<sub>2</sub>-ATP, 0.2 mM Na<sub>2</sub>-GTP.

### Network pharmacology methods to decipher possible mechanisms of SCT

Targets of the constituents identified from SCT in our previous study were obtained from Polypharmacology Browser 2 (<https://ppb2.gdb.tools/>) [[40](#block-19-0)]. Methods: ECfp4 Naive Bayes Machine Learning model produced on the fly with 2000 nearest neighbors from extended connectivity fingerprint ECfp4. Targets of neurodegenerative disorder were elements of the intersection set obtained from GeneCards [[41](#block-19-0)] (<https://www.genecards.org/>, Relevance score ≥ 10) and DisGeNET [[42](#block-19-0)] (<https://www.disgenet.org/>, Score gda ≥ 0.1) databases using following keywords: Alzheimer's disease, Parkinson's disease, amyotrophic lateral sclerosis, spinocerebellar ataxia, Lewy bodies, frontotemporal dementia, Huntington's disease and epilepsy.

Protein–protein interaction data were acquired from STRING 11.0 [[43](#block-19-0)] (<https://string-db.org/cgi/input.pl>) with the species limited to “Homo sapiens”.

GO and KEGG pathway enrichment analyses were performed by DAVID Bioinformatics Resources 6.8 [[44](#block-19-0)] (<https://david.ncifcrf.gov/>). The targets from the intersection set of targets of the constituents and diseases were submitted to obtain the terms of biological process, molecular function, cellular component and Kyoto Encyclopedia of Genes and Genomes (KEGG) pathways.

All visualized network models were established via Cytoscape 3.8.0. The topological feature of each node in network model was assessed by calculating three parameters named “Degree”, “Betweenness Centrality (BC)” and “Closeness Centrality (CC) by Network Analyze tool in Cytoscape software.

{5}------------------------------------------------

#### Preliminary verification for the possible mechanisms by surflex-dock

The constituents were prepared by Sybyl-X 2.0. As docking ligands, their energy was minimized according following parameter settings: Powell method, 0.005 kcal/mol·Å gradient termination, 1000 max iteration and Gasteiger-Huckel charges. Other settings were kept default.

The protein structures were obtained from PDB Protein Data Bank (<http://www.rcsb.org/>). To make docking pockets, the protein structures were extracted ligand substructure, repaired sidechains, added hydrogens and minimized their energy. Protomol generation mode was selected as “Ligand” and other settings were default. Reference molecules were set as their original ligands. Results of Total Score were output as the criterion to comparing the predictive affinities.

### Statistical method

Each value was an average of data from 3 independent experiments and each experiment included 3 replicates. Data were expressed as mean  $\pm$  SEM and analyzed using GraphPad Prism V8.0 (GraphPad Software, Inc., San Diego, CA, USA). One-way analysis of variance (ANOVA) and Dunnett’s test were used to evaluate statistical differences.

## Results

### SCT sub-fractions scavenge DPPH radical

The scavenging ability of DPPH radical of the SCT sub-fractions is depicted in Fig 2. The clearance percentages of four sub-fractions could all reach more than 40% at their highest concentration (500  $\mu$ g/mL). Fraction E3 was the most potent sub-fraction on scavenging DPPH radical among these four neuroprotective sub-fractions from SCT, although weaker than the positive compounds—vitamin C.

### SCT sub-fractions inhibit AChE

The AChE inhibition percent of four sub-fractions could reach more than 40% at their highest concentration (1000  $\mu$ g/mL). Since contrast to Huperzine-a AChE inhibitor, their effects on

![Bar chart showing DPPH clearance percentages of active sub-fractions (P5, P6, E1, E3) and Vitamin C at various concentrations (0, 0.5, 2.5, 5, 25, 50, 250, 500 μg/mL). The y-axis represents Clearance (%) from 0 to 100. The x-axis represents concentration in μg/mL. Legend: P5 (solid black), P6 (checkered), E1 (solid grey), E3 (white with black border), Vitamin C (diagonal stripes). Error bars represent SEM. 'NS' indicates no significant difference from the control group (0 μg/mL).](096d7a8a21933900dad68d82ae8a97fb_img.jpg)

| Concentration ( $\mu$ g/mL) | P5 | P6 | E1 | E3 | Vitamin C |
|-----------------------------|----|----|----|----|-----------|
| 0                           | 0  | 0  | 0  | 0  | 0         |
| 0.5                         | 16 | 14 | 12 | 14 | 16        |
| 2.5                         | 14 | 12 | 10 | 12 | 14        |
| 5                           | 12 | 10 | 8  | 10 | 12        |
| 25                          | 28 | 26 | 24 | 26 | 28        |
| 50                          | 41 | 39 | 37 | 39 | 41        |
| 250                         | 6  | 5  | 4  | 6  | 5         |
| 500                         | 6  | 5  | 4  | 6  | 5         |
| 250                         | 32 | 30 | 28 | 30 | 32        |
| 500                         | 51 | 49 | 47 | 49 | 51        |
| 25                          | 6  | 5  | 4  | 6  | 5         |
| 50                          | 8  | 7  | 6  | 8  | 7         |
| 250                         | 34 | 32 | 30 | 32 | 34        |
| 500                         | 58 | 56 | 54 | 56 | 58        |
| 25                          | 6  | 5  | 4  | 6  | 5         |
| 50                          | 12 | 10 | 9  | 11 | 10        |
| 250                         | 22 | 20 | 18 | 20 | 22        |
| 500                         | 70 | 68 | 66 | 68 | 70        |
| 25                          | 6  | 5  | 4  | 6  | 5         |
| 50                          | 88 | 86 | 84 | 86 | 88        |
| 250                         | 88 | 86 | 84 | 86 | 88        |
| 500                         | 88 | 86 | 84 | 86 | 88        |

Bar chart showing DPPH clearance percentages of active sub-fractions (P5, P6, E1, E3) and Vitamin C at various concentrations (0, 0.5, 2.5, 5, 25, 50, 250, 500 μg/mL). The y-axis represents Clearance (%) from 0 to 100. The x-axis represents concentration in μg/mL. Legend: P5 (solid black), P6 (checkered), E1 (solid grey), E3 (white with black border), Vitamin C (diagonal stripes). Error bars represent SEM. 'NS' indicates no significant difference from the control group (0 μg/mL).

Fig 2. The DPPH clearance percentages of active sub-fractions. Data were expressed as mean  $\pm$  S.E.M. from the data obtained from three independent experiments ( $n = 3$ ). NS represents the mean of group has no significant different with the mean of control group.

<https://doi.org/10.1371/journal.pone.0273583.g002>

{6}------------------------------------------------

![Bar chart showing the inhibition percentages of active sub-fractions (P5, P6, E1, E3) and Huperzine A on AChE at various concentrations (0, 10, 100, 1000 µg/mL). The y-axis represents Inhibition percent (%), ranging from 0 to 100. The x-axis represents concentration in µg/mL. Huperzine A shows the highest inhibition, reaching nearly 90% at 0.5 µg/mL. E1 shows the highest inhibition among the sub-fractions, reaching about 72% at 1000 µg/mL. P5 and P6 show moderate inhibition, while E3 shows very low inhibition.](c0843c6d138705289960d9f53a6e72a1_img.jpg)

| Concentration (µg/mL) | P5  | P6  | E1  | E3  | Huperzine A |
|-----------------------|-----|-----|-----|-----|-------------|
| 0                     | 0   | 0   | 0   | 0   | 0           |
| 10                    | ~5  | ~5  | ~10 | ~10 | ~10         |
| 100                   | ~20 | ~25 | ~15 | ~15 | ~15         |
| 1000                  | ~45 | ~58 | ~72 | ~15 | ~15         |
| 0.1                   | ~15 | ~35 | ~55 | ~55 | ~55         |
| 0.3                   | ~70 | ~85 | ~85 | ~85 | ~85         |
| 0.5                   | ~85 | ~90 | ~90 | ~90 | ~90         |

Bar chart showing the inhibition percentages of active sub-fractions (P5, P6, E1, E3) and Huperzine A on AChE at various concentrations (0, 10, 100, 1000 µg/mL). The y-axis represents Inhibition percent (%), ranging from 0 to 100. The x-axis represents concentration in µg/mL. Huperzine A shows the highest inhibition, reaching nearly 90% at 0.5 µg/mL. E1 shows the highest inhibition among the sub-fractions, reaching about 72% at 1000 µg/mL. P5 and P6 show moderate inhibition, while E3 shows very low inhibition.

**Fig 3.** The inhibition percentages of active sub-fractions on AChE. Data were expressed as mean  $\pm$  S.E.M. obtained from three independent experiments ( $n = 3$ ). NS represents the mean of group has no significant difference compared to the mean of control group.

<https://doi.org/10.1371/journal.pone.0273583.g003>

AChE were considered as slight efficacy. It also showed that fraction E1 exhibited more than 60% inhibition percent on AChE, which was the most potent sub-fraction among the extracts (Fig 3).

### SCT sub-fractions inhibit MAOs

The results depicted in [Fig 4](#block-7-0) showed, MAO-A selective inhibitor—clorgiline could inhibit the MAOs by about 60% at 50  $\mu$ M, while MAO-B selective inhibitor—pargyline could inhibit the MAOs by close to 100% at 50  $\mu$ M. Since the enzyme substrate was tyramine, which could be common enzyme substrate for both MAO-A and MAO-B, the enzyme activity of the MAOs we used in this study was considered to be contributed mainly by MAO-B [[45](#block-19-0)].

Except fraction E3, other three active sub-fractions presented more than 40% inhibition percent on MAOs at their highest concentration (1000  $\mu$ g/mL). The observed inhibition results were regarded as mild.

### SCT sub-fractions inhibit NMDAR

Compared to Zembrin<sup>®</sup>, the more potent neuroprotective P5 and E1 fractions (compared with P6 and E3 in our previous study [[20](#block-18-0)]) showed potent inhibiting effect on NMDAR-mediated current ([Fig 5](#block-8-0)). However, this effect is not significant enough to be considered as main mechanism that elicits antidepressant action of SCT.

### Common targets of constituents and neurodegenerative diseases

As indicated in the previous study, the neuroprotective sub-fractions and underlying neuroprotective constituents (structures were shown in [Fig 1](#block-2-0)) in SCT [[20](#block-18-0)]. Using Polypharmacology Browser 2, the predictive targets of the constituents from neuroprotective sub-fractions were compared with the targets of neurodegenerative diseases collected from GeneCards and DisGeNET databases. The results of their intersections were showed as [Fig 6](#block-9-0). Although the percent of overlapping targets in targets of HD was the maximum value (16.67%) among these neurodegenerative diseases, there were only 5 overlapping targets from the intersection.

{7}------------------------------------------------

![Bar chart showing the inhibition percentages of active sub-fractions (P5, P6, E1, E3) and reference drugs (Clorgiline, Pargyline) on MAOs. The Y-axis is 'Inhibition percent (%)' from 0 to 100. The X-axis shows concentrations in μg/mL and μM. P5, P6, E1, and E3 show varying inhibition percentages across different concentrations. Clorgiline and Pargyline show high inhibition percentages at higher concentrations.](a71911ad87414271aeb190e0eebcb989_img.jpg)

| Sub-fraction/Drug | Concentration (μg/mL) | Concentration (μM) | Inhibition Percent (%) |
|-------------------|-----------------------|--------------------|------------------------|
| P5                | 10                    | 0.1                | ~5                     |
|                   | 100                   | 0.1                | ~15                    |
|                   | 1000                  | 0.1                | ~48                    |
|                   | 10000                 | 0.1                | ~5                     |
| P6                | 10                    | 0.1                | ~5                     |
|                   | 100                   | 0.1                | ~20                    |
|                   | 1000                  | 0.1                | ~46                    |
|                   | 10000                 | 0.1                | ~20                    |
| E1                | 10                    | 0.1                | ~5                     |
|                   | 100                   | 0.1                | ~32                    |
|                   | 1000                  | 0.1                | ~58                    |
|                   | 10000                 | 0.1                | ~5                     |
| E3                | 10                    | 0.1                | ~15                    |
|                   | 100                   | 0.1                | ~28                    |
|                   | 1000                  | 0.1                | ~35                    |
|                   | 10000                 | 0.1                | ~15                    |
| Clorgiline        | 0.5                   | 0.5                | ~35                    |
|                   | 5                     | 0.5                | ~64                    |
|                   | 50                    | 0.5                | ~55                    |
|                   | 500                   | 0.5                | ~83                    |
| Pargyline         | 0.5                   | 0.5                | ~35                    |
|                   | 5                     | 0.5                | ~38                    |
|                   | 50                    | 0.5                | ~63                    |
|                   | 500                   | 0.5                | ~100                   |

Bar chart showing the inhibition percentages of active sub-fractions (P5, P6, E1, E3) and reference drugs (Clorgiline, Pargyline) on MAOs. The Y-axis is 'Inhibition percent (%)' from 0 to 100. The X-axis shows concentrations in μg/mL and μM. P5, P6, E1, and E3 show varying inhibition percentages across different concentrations. Clorgiline and Pargyline show high inhibition percentages at higher concentrations.

**[Fig 4.](#block-6-0) The inhibition percentages of active sub-fractions on MAOs.** Data were expressed as mean  $\pm$  S.E.M. obtained from three independent experiments (n = 3). NS represents the mean of group showed no significant difference with the mean of control group.

<https://doi.org/10.1371/journal.pone.0273583.g004>

Therefore, AD or PD was selected as adaptable disease because of the larger number and percentage of common targets ([Table 1](#block-9-0)) than other disease conditions.

#### GO and KEGG pathway enrichment analysis

The overlapping targets of constituents and AD/PD could enrich in more than 20 terms of biological processes (the terms of which P value < 0.001 were showed as [Fig 7](#block-10-0)), which mainly involved response to drug (GO:0042493), chemical synaptic transmission (GO:0007268), locomotory behavior (GO:0007626), memory (GO:0007613), learning (GO:0007612, GO:0008542), response to amphetamine (GO:0001975), behavioral response to cocaine (GO:0048148), dopaminergic synaptic transmission (GO:0001963), prepulse inhibition (GO:0060134), etc. These biological processes indicate that the extracts of SCT could exert neurological activities that are helpful to treat cognition deficit and behavioral disorders. The analysis of cellular functions ([Fig 8](#block-11-0)) showed that these targets mainly included dopamine binding (GO:0035240), dopamine neurotransmitter receptor activity (GO:0004952), beta-amyloid binding (GO:0001540), drug binding (GO:0008144), enzyme binding (GO:0019899), etc. Moreover, these overlapping targets are mainly integral component of plasma membrane (GO:0005887), locate on plasma membrane (GO:0016021) and cell surface (GO:0009986), distribute on dendrite (GO:0030425) and axon (GO:0030424) ([Fig 8](#block-11-0)). KEGG pathway analysis of these targets suggested that they play a role in neuroactive ligand-receptor interaction (hsa04080), serotonergic synapse (hsa04726), dopaminergic synapse (hsa04728), Alzheimer's disease (hsa05010), alcoholism (hsa05034), cAMP signaling pathway (hsa04024), Parkinson's disease (hsa05012), calcium signaling pathway (hsa04020), amphetamine addiction (hsa05031) ([Fig 9](#block-12-0)).

{8}------------------------------------------------

![Bar chart showing the inhibition percentages of active sub-fractions on NMDAR-mediated current. The Y-axis is 'Inhibition percent (%) of NMDA receptor mediated current' (0-120). The X-axis shows concentrations in μg/mL (0, 1, 50, 100) and μM (1, 25, 50, 100). Four groups are compared: P5 (solid black), E1 (solid black), Zembrin® (white with cross-hatch), and D-AP5 (white with diagonal lines). P5 and E1 show significant inhibition at 50 and 100 μg/mL. Zembrin® shows significant inhibition at 50 and 100 μM. D-AP5 shows the highest inhibition at 100 μM (~85%). 'ns' indicates no significant difference from the control group (0 concentration).](91be14371a97fb5ce9eeb29ae18d07c3_img.jpg)

| Group    | Concentration | Inhibition (%) | Significance |
|----------|---------------|----------------|--------------|
| P5       | 0             | 0              |              |
|          | 1             | ~10            | ns           |
|          | 50            | ~30            |              |
|          | 100           | ~35            |              |
| E1       | 0             | 0              |              |
|          | 1             | ~5             | ns           |
|          | 25            | ~15            |              |
|          | 50            | ~28            |              |
| Zembrin® | 0             | 0              |              |
|          | 1             | ~5             | ns           |
|          | 50            | ~18            |              |
|          | 100           | ~23            |              |
| D-AP5    | 100           | ~85            |              |

Bar chart showing the inhibition percentages of active sub-fractions on NMDAR-mediated current. The Y-axis is 'Inhibition percent (%) of NMDA receptor mediated current' (0-120). The X-axis shows concentrations in μg/mL (0, 1, 50, 100) and μM (1, 25, 50, 100). Four groups are compared: P5 (solid black), E1 (solid black), Zembrin® (white with cross-hatch), and D-AP5 (white with diagonal lines). P5 and E1 show significant inhibition at 50 and 100 μg/mL. Zembrin® shows significant inhibition at 50 and 100 μM. D-AP5 shows the highest inhibition at 100 μM (~85%). 'ns' indicates no significant difference from the control group (0 concentration).

**[Fig 5.](#block-6-0) The inhibition percentages of active sub-fractions on NMDAR-mediated current.** Data were expressed as mean  $\pm$  S.E.M. D-AP5 group: n = 4, other groups: n = 3. NS represents the mean of group has no significant different with the mean of control group.

<https://doi.org/10.1371/journal.pone.0273583.g005>

#### Constituents-targets-disease network diagram

The interactions of the overlapping targets, constituents and their possible targets and targets of AD or PD were fed into cytoscape 3.8.0 software to obtain a constituents-targets-disease network diagram ([Fig 10](#block-13-0)). In this network diagram, there were 59 nodes and 345 edges, including 23 constituents, 30 targets, 2 diseases, 4 sub-fractions and 1 plant. The result of network analysis ([Table 2](#block-14-0)) showed that degrees of the targets, of which gene names are SLC6A4, DRD2, ACHE, HTR1A, SLC6A3, HTT, APP, HTR2A, MAOB, BACE1, DRD3, TNF, CNR2, BCHE, DRD1 and GRIN2B, are more than 13 with betweenness centralities more than 0.005 and closeness centralities more than 0.5. The degrees of all constituents in this diagram are equal or greater than 6.

### Key targets in the possible mechanisms of SCT in the treatment of AD or PD

Targets with a greater degree value (more than 13) or enriched in AD or PD KEGG pathway were selected to be docked with constituents from neuroprotective sub-fractions by Surflex-Dock (Total Score results showed as [Fig 11](#block-15-0)).

The Total Score results indicated that many vital targets involved in AD or PD, for example AChE (ACHE), MAO-B (MAOB), GluN2B-NMDAR (GRIN2B), adenosine A2A receptor (A2AR, ADORA2A) and cannabinoid receptor 2 (CB2R, CNR2), have potent predicted binding activity with several SCT constituents. Moreover, SCT constituents as [Fig 12](#block-16-0) showed have higher Total Score with corresponding targets, which indicated that they are more possible to affect the targets to exert neuroprotective efficacy for the treatment of AD or PD.

{9}------------------------------------------------

### The targets intersection of neurodegenerative diseases and neuroprotective sub-fractions

![Figure 6: A dual-axis chart showing the intersection of targets from constituents and diseases. The x-axis lists diseases: AD, PD, ALS, SCA, LBD, FTD, HD, and Epilepsy. The left y-axis (black bars) represents the 'Number of common targets (column)' from 0 to 45. The right y-axis (red line with dots) represents 'Common targets percent in targets of the disease (curve)' from 0 to 20. The data points are: AD (22 targets, 10.5%), PD (15 targets, 12.5%), ALS (4 targets, 4%), SCA (0 targets, 0%), LBD (2 targets, 10%), FTD (0 targets, 0%), HD (5 targets, 16.7%), Epilepsy (4 targets, 4%).](f519a5be118c846f631c992412353fb9_img.jpg)

| Disease  | Number of common targets (column) | Common targets percent in targets of the disease (curve) |
|----------|-----------------------------------|----------------------------------------------------------|
| AD       | 22                                | 10.5%                                                    |
| PD       | 15                                | 12.5%                                                    |
| ALS      | 4                                 | 4%                                                       |
| SCA      | 0                                 | 0%                                                       |
| LBD      | 2                                 | 10%                                                      |
| FTD      | 0                                 | 0%                                                       |
| HD       | 5                                 | 16.7%                                                    |
| Epilepsy | 4                                 | 4%                                                       |

Figure 6: A dual-axis chart showing the intersection of targets from constituents and diseases. The x-axis lists diseases: AD, PD, ALS, SCA, LBD, FTD, HD, and Epilepsy. The left y-axis (black bars) represents the 'Number of common targets (column)' from 0 to 45. The right y-axis (red line with dots) represents 'Common targets percent in targets of the disease (curve)' from 0 to 20. The data points are: AD (22 targets, 10.5%), PD (15 targets, 12.5%), ALS (4 targets, 4%), SCA (0 targets, 0%), LBD (2 targets, 10%), FTD (0 targets, 0%), HD (5 targets, 16.7%), Epilepsy (4 targets, 4%).

**[Fig 6.](#block-6-0) The intersection of targets from constituents and diseases.** AD: Alzheimer's Disease; PD: Parkinson's Disease; ALS: Amyotrophic Lateral Sclerosis; SCA: Spinocerebellar Ataxia; LBD: Lewy Body Dementia; FTD: Frontotemporal Dementia; HD: Huntington's Disease.

<https://doi.org/10.1371/journal.pone.0273583.g006>

**[Table 1.](#block-7-0) Overlapping targets of constituents and AD/PD.**

| Gene   | Common name                                                    |
|--------|----------------------------------------------------------------|
| ESR2   | Estrogen receptor beta                                         |
| MAOB   | Monoamine oxidase type B                                       |
| HTR6   | 5-hydroxytryptamine receptor 6                                 |
| CYP2D6 | Cytochrome P450 2D6                                            |
| ACHE   | Acetylcholinesterase                                           |
| SLC6A4 | Sodium-dependent serotonin transporter                         |
| SLC6A3 | Sodium-dependent dopamine transporter                          |
| BACE1  | Beta-secretase 1                                               |
| HTR2A  | 5-hydroxytryptamine receptor 2A                                |
| CNR2   | Cannabinoid receptor 2                                         |
| BCHE   | Cholinesterase                                                 |
| ALOX5  | Polyunsaturated fatty acid 5-lipoxygenase                      |
| APP    | Amyloid-beta precursor protein                                 |
| TPO    | Translocator protein                                           |
| GSK3B  | Glycogen synthase kinase-3 beta                                |
| PTGS2  | Prostaglandin G/H synthase 2                                   |
| ADAM17 | Disintegrin and metalloproteinase domain-containing protein 17 |
| BACE2  | Beta-secretase 2                                               |
| GRIN2B | N-methyl D-aspartate receptor subtype 2B                       |

(Continued)

{10}------------------------------------------------

Table 1. (Continued)

| Gene    | Common name                     |
|---------|---------------------------------|
| CTSD    | Cathepsin D                     |
| TNF     | Tumor necrosis factor           |
| HTR1A   | 5-hydroxytryptamine receptor 1A |
| DRD3    | Dopamine D3 receptor            |
| DRD2    | Dopamine D2 receptor            |
| DRD1    | Dopamine D1 receptor            |
| ADORA2A | Adenosine receptor A2a          |
| HTT     | Huntingtin                      |

<https://doi.org/10.1371/journal.pone.0273583.t001>

## Discussion

The outcomes of this study demonstrated the efficacies of SCT neuroprotective sub-fractions in scavenging DPPH radical, inhibiting AChE, MAOs and NMDAR by experiments performed using *in vitro* models.

![Enrichment analysis dot plot showing biological processes and their enrichment factors. The Y-axis lists GO terms, and the X-axis shows the Enrich factor (0.0 to 0.6). Points are colored by -log10(pvalue) and size by count.](72d357d406618f3f884c3876fc3058ee_img.jpg)

### Biological process

Term

GO:0051584~regulation of dopamine uptake involved in synaptic transmission

GO:0060134~prepulse inhibition

GO:0001963~synaptic transmission, dopaminergic

GO:0042053~regulation of dopamine metabolic process

GO:0048148~behavioral response to cocaine

GO:0042417~dopamine metabolic process

GO:0035815~positive regulation of renal sodium excretion

GO:0014059~regulation of dopamine secretion

GO:0007210~serotonin receptor signaling pathway

GO:0001975~response to amphetamine

GO:0051968~positive regulation of synaptic transmission, glutamatergic

GO:0001659~temperature homeostasis

GO:0006509~membrane protein ectodomain proteolysis

GO:0008542~visual learning

GO:0007612~learning

GO:0007613~memory

GO:0007626~locomotory behavior

GO:0042493~response to drug

GO:0045471~response to ethanol

GO:0007268~chemical synaptic transmission

Enrich factor

count

- 5.0
- 7.5
- 10.0

$-\log_{10}(\text{pvalue})$

- 10.0
- 7.5
- 5.0

Enrichment analysis dot plot showing biological processes and their enrichment factors. The Y-axis lists GO terms, and the X-axis shows the Enrich factor (0.0 to 0.6). Points are colored by -log10(pvalue) and size by count.

[Fig 7.](#block-7-0) Enrichment analyses for constituents-AD/PD common targets: Biological process.

<https://doi.org/10.1371/journal.pone.0273583.g007>

{11}------------------------------------------------

![Figure 8: Enrichment analyses for constituents-AD/PD common targets. The figure consists of two scatter plots: 'Molecular function' on the left and 'Cellular component' on the right. Both plots show GO terms on the y-axis, Enrich factor on the x-axis, and -log10(pvalue) as color intensity. The 'Molecular function' plot shows terms like acetylcholinesterase activity, cholinesterase activity, dopamine neurotransmitter receptor activity, and enzyme binding. The 'Cellular component' plot shows terms like nuclear envelope lumen, dendritic shaft, and plasma membrane. Data points are colored based on their count (2, 3, 4, 5, 6) and -log10(pvalue) (3, 4, 5, 6, 7).](f176174c2978785e86a8352bd45e322e_img.jpg)

Figure 8: Enrichment analyses for constituents-AD/PD common targets. The figure consists of two scatter plots: 'Molecular function' on the left and 'Cellular component' on the right. Both plots show GO terms on the y-axis, Enrich factor on the x-axis, and -log10(pvalue) as color intensity. The 'Molecular function' plot shows terms like acetylcholinesterase activity, cholinesterase activity, dopamine neurotransmitter receptor activity, and enzyme binding. The 'Cellular component' plot shows terms like nuclear envelope lumen, dendritic shaft, and plasma membrane. Data points are colored based on their count (2, 3, 4, 5, 6) and -log10(pvalue) (3, 4, 5, 6, 7).

**[Fig 8.](#block-7-0) Enrichment analyses for constituents-AD/PD common targets: Molecular function and cellular component.**

<https://doi.org/10.1371/journal.pone.0273583.g008>

The clearance percent of four sub-fractions could reach more than 40% at 500  $\mu\text{g/mL}$ . In contrast to the radical scavenging efficacy of SCT extract in the previous study, E3 could present comparative performance on scavenging DPPH radical [[46](#block-19-0)], which indicated the constituents with antioxidant effect of SCT was enriched in the ethyl acetate sub-fraction. Antioxidative effect is a known mechanism of certain compounds eliciting neuroprotective action [[7](#block-17-0), [47](#block-19-0)–[49](#block-19-0)]. The results further suggest that SCT has potential to treat neurodegenerative disorders through its antioxidative effect.

The study also showed moderate inhibiting effect of SCT neuroprotective sub-fractions on AChE, which was more potent than the effect of SCT extract in previous study based on comparing their test concentrations [[50](#block-20-0)]. The reduction of acetylcholine level in AD patient may cause cognitive and memory impairments [[51](#block-20-0)]. Hence, AChE may accelerate the progression of AD though promoting the fibration of  $\beta$ -amyloid [[52](#block-20-0)]. Scopolamine, a muscarinic receptor antagonist, produces a blocking of the activity of the muscarinic acetylcholine receptor, and the concomitant appearance of transient cognitive amnesia and electrophysiological changes, which resemble those observed in AD [[53](#block-20-0), [54](#block-20-0)]. There are certain AChE inhibitors approved for AD, for example, donepezil and galanthamine. In fact, some studies had described the neuroprotective effect of AChE inhibitor [[22](#block-18-0), [23](#block-18-0)]. Hence, inhibiting AChE appears to be an underlying mechanism of the neuroprotective action of SCT.

The results of MAOs inhibiting assay showed, except E3, other three active sub-fractions (P5, P6 and E1) all presented more than 40% inhibition percent on MAOs at 1000  $\mu\text{g/mL}$ , which is still more potent than the inhibiting effect of SCT extract on MAO-A by comparing their concentrations [[50](#block-20-0)]. Since MAO-A selective inhibitor (clorgyline) could not inhibit the crude MAOs close to 100% at 50  $\mu\text{M}$ , while MAO-B selective inhibitor (pargyline) could inhibit it close to 100% at 50  $\mu\text{M}$ . This result indicated that enzyme activity of the crude MAOs used in this study mainly contributed by MAO-B [[39](#block-19-0), [45](#block-19-0)]. Excess MAOs catalyze oxidation of amino substance causing the generation of oxidative stress [[55](#block-20-0), [56](#block-20-0)]. Moreover, a MAO-B inhibitor—selegiline approved for PD was reported to suppress excess GABA produced from astrocytes and restores the impaired spike probability, synaptic plasticity, and learning and memory in the mice [[24](#block-18-0)]. However, some clinical trials showed that the cognitive function of the placebo group had no significant difference compared to the group treated

{12}------------------------------------------------

![KEGG pathway enrichment plot showing Enrich factor vs Term. The plot displays various KEGG pathways with their enrichment factors and -log10(pvalue).](b05a8a3551db31147979064952179990_img.jpg)

The figure is a scatter plot titled "KEGG pathway" showing enrichment analysis results. The y-axis is labeled "Term" and lists KEGG pathway IDs and names. The x-axis is labeled "Enrich factor" and ranges from 0.02 to 0.10. Data points are colored circles representing the enrichment factor, with size indicating the count of constituents and color indicating the -log10(pvalue).

| Term                                             | Enrich factor | Count | -log10(pvalue) |
|--------------------------------------------------|---------------|-------|----------------|
| hsa05030:Cocaine addiction                       | ~0.105        | 10    | ~2.5           |
| hsa04726:Serotonergic synapse                    | ~0.082        | 6     | ~8.5           |
| hsa05031:Amphetamine addiction                   | ~0.062        | 4     | ~2.5           |
| hsa04728:Dopaminergic synapse                    | ~0.052        | 8     | ~2.5           |
| hsa05010:Alzheimer's disease                     | ~0.042        | 4     | ~2.5           |
| hsa04080:Neuroactive ligand-receptor interaction | ~0.035        | 10    | ~6.5           |
| hsa04540:Gap junction                            | ~0.032        | 4     | ~2.5           |
| hsa05034:Alcoholism                              | ~0.032        | 4     | ~2.5           |
| hsa04024:cAMP signaling pathway                  | ~0.032        | 4     | ~2.5           |
| hsa05012:Parkinson's disease                     | ~0.032        | 4     | ~2.5           |
| hsa04020:Calcium signaling pathway               | ~0.025        | 4     | ~2.5           |

KEGG pathway enrichment plot showing Enrich factor vs Term. The plot displays various KEGG pathways with their enrichment factors and -log10(pvalue).

[Fig 9.](#block-7-0) Enrichment analyses for constituents-AD/PD common targets: KEGG pathway.

<https://doi.org/10.1371/journal.pone.0273583.g009>

with selegiline for a long term therapy [[25](#block-18-0), [26](#block-18-0)]. Instead of irreversible inhibitor like selegiline, a reversible MAO-B inhibitor (KDS2010) does not induce compensatory mechanisms in a long term therapy, which further attenuated increased astrocytic GABA levels and astrogliosis, enhanced synaptic transmission, rescued learning and memory impairments in APP/PS1 mice [[27](#block-18-0)]. Thereby, MAO-B is considered as a key target of SCT in the treatment of AD or PD.

Furthermore, P5 and E1 fractions SCT presented a non-significant inhibition of NMDAR-mediated current in hippocampal neurons of Sprague-Dawley neonatal rats, which was more potent than the effect of Zembrin<sup>®</sup> on NMDAR-mediated current and consistent with previous results [[57](#block-20-0)]. NMDAR, an ionotropic glutamate receptor, which constitute a calcium-permeable component of fast excitatory neurotransmission, have been verified to participate neuro-physiologically in many cell signaling pathways resulting in several neurological diseases. An NMDAR inhibitor—esketamine was approved for depressive disorder owing to its rapid antidepressant action. The previous studies showed the potential of SCT on treating depressive disorder [[2](#block-17-0), [4](#block-17-0), [28](#block-18-0)–[33](#block-19-0)]. However, the results of this study indicated that the influence on NMDAR of these two fractions may be a subsequent effect resulted from affecting other targets but not NMDAR. Thus leading to a possibility that the anti-depressive action of SCT

{13}------------------------------------------------

![SCT-sub-fraction-constituents-targets-disease network diagram](4ee27dbf5ef12e7b58b0ef0937bc5a5e_img.jpg)

A complex network diagram illustrating the relationships between *Sceletium tortuosum* (SCT) sub-fractions, their constituents, targets, and associated diseases. The network is structured as a multi-layered graph with nodes of various colors and shapes, connected by numerous grey lines representing interactions.

**Legend:**

- Plant (Blue rectangle)
- Subfraction (Cyan rectangle)
- Constituent (Green diamond)
- Target (Red oval)
- Disease (Yellow hexagon)

**Nodes and Labels:**

- Plant:** SCT
- Subfractions:** E3, P6, E1, P5
- Constituents (Green diamonds):** 1.44, 2.67, 3.28, 3.45, 3.86, 3.26, 4.97, 1.15, 3.71, 1.24, 3.5, 4.73, 2.12, 1.93, 4.15, 4.03, 3.261, 4.07, 3.35, 2.97, 3.1, 2.75, 1.2
- Targets (Red ovals):** BACE1, MAOB, APP, HTR2A, HTT, SLC6A3, AChE, HTR1A, DRD2, SLC6A4, RPK1, TRAF2, TNFRSF1A, CTSD, ESR2, TSP0, BACE2, ADAM17, HTR6, ALOX5, GSK3B, CYP2D6, PTGS2, GRIN2B, DRD1, BCHE, TNF, CNR2, DRD3
- Diseases (Yellow hexagons):** PD, AD

SCT-sub-fraction-constituents-targets-disease network diagram

[Fig 10.](#block-8-0) SCT-sub-fraction-constituents-targets-disease network diagram.

<https://doi.org/10.1371/journal.pone.0273583.g010>

{14}------------------------------------------------

[Table 2.](#block-8-0) The results of topological analysis for the network.

| Node Name | Degree | Betweenness Centrality | Closeness Centrality |
|-----------|--------|------------------------|----------------------|
| SLC6A4    | 32     | 0.06260                | 0.62766              |
| DRD2      | 31     | 0.05874                | 0.64130              |
| ACHE      | 30     | 0.10778                | 0.65556              |
| HTR1A     | 30     | 0.07519                | 0.64130              |
| SLC6A3    | 26     | 0.03614                | 0.59596              |
| HTT       | 23     | 0.03893                | 0.57282              |
| APP       | 20     | 0.04156                | 0.57843              |
| HTR2A     | 20     | 0.02568                | 0.56731              |
| MAOB      | 20     | 0.02614                | 0.55140              |
| BACE1     | 19     | 0.05334                | 0.57282              |
| DRD3      | 17     | 0.01538                | 0.55660              |
| TNF       | 15     | 0.08981                | 0.52679              |
| CNR2      | 15     | 0.02514                | 0.55140              |
| BCHE      | 14     | 0.01292                | 0.53636              |
| DRD1      | 13     | 0.00678                | 0.52212              |
| GRIN2B    | 13     | 0.00617                | 0.52212              |
| PTGS2     | 12     | 0.02749                | 0.51754              |
| CYP2D6    | 12     | 0.00583                | 0.53153              |
| GSK3B     | 10     | 0.01317                | 0.47967              |
| ADAM17    | 7      | 0.00234                | 0.45385              |
| ADORA2A   | 7      | 0.00621                | 0.50000              |
| ALOX5     | 7      | 0.00475                | 0.45385              |
| HTR6      | 7      | 0.00442                | 0.49167              |
| BACE2     | 6      | 0.00107                | 0.43704              |
| CTSD      | 5      | 0.00113                | 0.42143              |
| ESR2      | 5      | 0.00722                | 0.42143              |
| Tspo      | 5      | 0.00034                | 0.41259              |
| TNFRSF1A  | 4      | 0.00171                | 0.36646              |
| RIPK1     | 3      | 0                      | 0.35119              |
| TRAF2     | 3      | 0                      | 0.35119              |
| 1.19      | 12     | 0.02202                | 0.51304              |
| 4.97      | 11     | 0.00727                | 0.50000              |
| 3.45      | 10     | 0.00977                | 0.50000              |
| 3.86      | 10     | 0.01547                | 0.50000              |
| 5.26      | 10     | 0.03077                | 0.50427              |
| 1.44      | 9      | 0.00425                | 0.49580              |
| 3.28      | 9      | 0.00307                | 0.50000              |
| 1.24      | 9      | 0.00949                | 0.49580              |
| 2.67      | 9      | 0.00869                | 0.48361              |
| 2.12      | 8      | 0.00342                | 0.48361              |
| 2.731     | 8      | 0.00244                | 0.49167              |
| 3.50      | 8      | 0.00250                | 0.47967              |
| 1.93      | 8      | 0.00212                | 0.45385              |
| 2.73      | 7      | 0.02801                | 0.45385              |
| 4.03      | 7      | 0.00167                | 0.47581              |
| 4.14      | 7      | 0.00193                | 0.47581              |
| 2.11      | 7      | 0.00152                | 0.45038              |

(Continued)

{15}------------------------------------------------

Table 2. (Continued)

| Node Name | Degree | Betweenness Centrality | Closeness Centrality |
|-----------|--------|------------------------|----------------------|
| 2.97      | 7      | 0.00471                | 0.47967              |
| 3.35      | 7      | 0.01321                | 0.50427              |
| 4.07      | 7      | 0.00184                | 0.48361              |
| 5.261     | 7      | 0.00153                | 0.47200              |
| 3.71      | 6      | 0.00130                | 0.46825              |
| 4.22      | 6      | 0.00612                | 0.45385              |

<https://doi.org/10.1371/journal.pone.0273583.t002>

extract can be due to inhibition efficacy of mesembrine and mesembrenone on phosphodiesterase-4 and serotonin transporter [[58](#block-20-0)].

Therefore, results of the *in vitro* experiments indicated that there are neuroprotective constituents in SCT could protect neurons to treat neurodegenerative disorders by scavenging radicals, inhibiting AChE, MAOs and NMDAR. Different sub-fractions represented different degrees of influence on AChE, MAOs and NMDAR.

Moreover, the neuroprotective sub-fractions of SCT used to assess the potential use to treat AD or PD, was further supported by network pharmacology related methods applied in this study, which was also supported by the observed influence of SCT extract on cognition [[5](#block-17-0), [6](#block-17-0)]. Among several neurodegenerative disorders, the targets of AD or PD from database have most overlapping numbers with the targets predicted by Polypharmacology Browser 2. It is understood that the overlapping targets could be involved in memory, learning and behavior related biological process and enrich in AD and PD corresponding KEGG pathway. The network analysis and Surflex-Dock results have indicated that some key targets, AChE, MAO-B, GluN2B-NMDAR, A2AR and CB2R, can be influenced by SCT in the probable treatment of

![Heatmap showing Surflex-Dock results of SCT constituents with key targets in total score. The heatmap displays the docking score for various compounds (P5, P6, E1, E3) against a list of targets (SLC6A4, DRD2, AChE, SLC6A3, MAOB, HTR2A, BACE1, DRD3, CNR2, TNF, BCHE, GRIN2B, ADAM17, GSK3B, BACE2, DRD1, ADORA2A). The color scale ranges from 0 (white) to 10 (black).](0bd23f00e0632855cfef9274f1ab93d8_img.jpg)

Surflex-Dock result (Total Score)

Compounds from SCT active fractions (retention time (min) in UPLC)

Legend: 0, 5, 10

Heatmap showing Surflex-Dock results of SCT constituents with key targets in total score. The heatmap displays the docking score for various compounds (P5, P6, E1, E3) against a list of targets (SLC6A4, DRD2, AChE, SLC6A3, MAOB, HTR2A, BACE1, DRD3, CNR2, TNF, BCHE, GRIN2B, ADAM17, GSK3B, BACE2, DRD1, ADORA2A). The color scale ranges from 0 (white) to 10 (black).

[Fig 11.](#block-8-0) Surflex-dock results of SCT constituents with key targets in total score.

<https://doi.org/10.1371/journal.pone.0273583.g011>

{16}------------------------------------------------

![Figure 12: Constituents from SCT with their possible targets predicted by total score in surflex-dock. The figure is divided into five sections, each showing chemical structures and their predicted targets.](6703b55796811c3389650d3f052b27d8_img.jpg)

**AChE**

N-trans-feruloyl-3-methyldopamine tR = 4.22 min

Dihydrojoubertamine tR = 2.73 min

Egonie tR = 3.86 min

N-Methyldihydrojoubertamine tR = 4.97 min

**MAO-B**

N-trans-feruloyl-3-methyldopamine tR = 4.22 min

Egonie tR = 5.261 min

Dihydrojoubertamine tR = 2.73 min

N-demethyl-N-formylmesembrenone tR = 3.50 min

**GluN2B-NMDAR**

N-trans-feruloyl-3-methyldopamine tR = 4.22 min

Dihydrojoubertamine tR = 2.73 min

**CB2R**

N-Methyldihydrojoubertamine tR = 4.97 min

Sceletium A4 tR = 1.93 min

**A2AR**

N-trans-feruloyl-3-methyldopamine tR = 4.22 min

Dihydrojoubertamine tR = 2.73 min

tR = 5.26 min

Figure 12: Constituents from SCT with their possible targets predicted by total score in surflex-dock. The figure is divided into five sections, each showing chemical structures and their predicted targets.

Fig 12. Constituents from SCT with their possible targets predicted by total score in surflex-dock.

<https://doi.org/10.1371/journal.pone.0273583.g012>

AD or PD, and other constituents SCT or similar moieties of close chemical structures, such as egonie, sceletium A4, dihydrojoubertamine, N-trans-feruloyl-3-methyldopamine, N-methyldihydrojoubertamine and so on, should be concerned to have potential in affecting on corresponding targets (Fig 12).

In this study, the primary purpose was to explore possible targets of the neuroprotective SCT on neurodegenerative disorders by network pharmacology. According to the identified constituents from SCT in our previous study, the results of network pharmacology studies indicated some potential targets (AChE, MAOs and NMDAR) for SCT. Therefore, the neuroprotective SCT sub-fractions were further tested in vitro for their efficacy on the potential targets. Encouragingly, the results of the fraction-targets in vitro experiments actually supported the network pharmacology results in this study. However, different sub-fractions contained different natural products, the content of natural products were also various, which resulted in the different effects of different sub-fractions to these potential target in this study. Certainly, in the next stage, the further studies would carry out to explain the bioactivity mechanism of different sub-fractions on their specific targets.

{17}------------------------------------------------

## Conclusion

SCT neuroprotective sub-fractions have moderate potency of scavenging radicals, inhibiting AChE, MAOs and NMDAR, which are the possible mechanisms of its neuroprotective effect. The identified and other related constituents in SCT may have affects on biological systems to alter AChE, MAO-B, GluN2B-NMDAR, A2AR and CB2R, to exert their therapeutic potential in the probable treatment of AD or PD.

## Author Contributions

**Data curation:** Yangwen Luo.

**Formal analysis:** Yangwen Luo.

**Methodology:** Luchen Shan, Lipeng Xu.

**Project administration:** Pei Yu, Xu Jun.

**Resources:** Srinivas Patnala, Isadore Kanfer.

**Validation:** Yangwen Luo.

**Visualization:** Yangwen Luo.

**Writing – original draft:** Yangwen Luo.

**Writing – review & editing:** Yangwen Luo, Srinivas Patnala, Isadore Kanfer, Jiahao Li.

## References

- [1](#block-0-0). Filipovic SR, Covickovic-Sternic N, Stojanovic-Svetel M, Lecic D, Kostic VS. Depression in Parkinson's disease: an EEG frequency analysis study. *Parkinsonism Relat Disord*. 1998; [4](#block-1-0)(4):1[7](#block-11-0)1–8. [https://doi.org/10.1016/s1353-8020\(98\)00027-3](https://doi.org/10.1016/s1353-8020(98)00027-3) PMID: [18591107](http://www.ncbi.nlm.nih.gov/pubmed/18591107)
- [2](#block-12-0). Gericke N, Harvey A, Viljoen A, Hofmeyr D, inventors; H.L. Hall & Sons Limited, S. Afr.. assignee. Sceletium extract and uses thereof patent US2012000427[5](#block-1-0)A1. 2012.
- [3](#block-1-0). Dimpfel W, inventor; HG&H Pharmaceuticals Pty. Ltd., S. Afr.. assignee. Mesembrenol and/or mesembranol for prophylaxis and treatment of patients suffering from epilepsy and associated diseases patent WO201902119[6](#block-1-0)A1. 2019.
4. Loria MJ, Ali Z, Abe N, Sufka KJ, Khan IA. Effects of Sceletium tortuosum in rats. *Journal of Ethnopharmacology*. 2014; 155(1):731–5. <https://doi.org/10.1016/j.jep.2014.06.007> PMID: [24930358](http://www.ncbi.nlm.nih.gov/pubmed/24930358)
5. Chiu S, Gericke N, Farina-Woodbury M, Badmaev V, Raheb, et al. Proof-of-Concept Randomized Controlled Study of Cognition Effects of the Proprietary Extract Sceletium tortuosum (Zembrin) Targeting Phosphodiesterase-4 in Cognitively Healthy Subjects: Implications for Alzheimer's Dementia. *Evid Based Complement Alternat Med*. 2014; 2014:682014. <https://doi.org/10.1155/2014/682014> PMID: [25389443](http://www.ncbi.nlm.nih.gov/pubmed/25389443)
6. Hoffman JR, Markus I, Dubnov-Raz G, Gepner Y. Ergogenic Effects of 8 Days of Sceletium Tortuosum Supplementation on Mood, Visual Tracking, and Reaction in Recreationally Trained Men and Women. *J Strength Cond Res*. 2020; 34(9):2476–81. <https://doi.org/10.1519/JSC.0000000000003693> PMID: [32740286](http://www.ncbi.nlm.nih.gov/pubmed/32740286)
7. Singh SK, Srivastav S, Castellani RJ, Plascencia-Villa G, Perry G. Neuroprotective and Antioxidant Effect of Ginkgo biloba Extract Against AD and Other Neurological Disorders. *Neurotherapeutics*. 2019; 16(3):666–74. <https://doi.org/10.1007/s13311-019-00767-8> PMID: [31376068](http://www.ncbi.nlm.nih.gov/pubmed/31376068)
8. Davies J, Chen J, Pink R, Carter D, Saunders N, Sotiriadis G, et al. Orexin receptors exert a neuroprotective effect in Alzheimer's disease (AD) via heterodimerization with GPR103. *Sci Rep*. 2015; 5:12584. <https://doi.org/10.1038/srep12584> PMID: [26223541](http://www.ncbi.nlm.nih.gov/pubmed/26223541)
9. Chen P-H, Cheng F-Y, Cheng S-J, Shaw J-S. Predicting cognitive decline in Parkinson's disease with mild cognitive impairment: a one-year observational study. *Parkinson's Dis*. 2020:8983960. <https://doi.org/10.1155/2020/8983960> PMID: [33178412](http://www.ncbi.nlm.nih.gov/pubmed/33178412)
10. Enache D, Pereira JB, Jelic V, Winblad B, Nilsson P, Aarsland D, et al. Increased Cerebrospinal Fluid Concentration of ZnT3 Is Associated with Cognitive Impairment in Alzheimer Disease. *J Alzheimer's Dis*. 2020; 77(3):1143–55.

{18}------------------------------------------------

11. Scott XO, Stephens ME, Desir MC, Dietrich WD, Keane RW, Pablo de Rivero Vaccari J. The inflammatory adaptor protein ASC in mild cognitive impairment and Alzheimer's disease. *Int J Mol Sci*. [20](#block-1-0)20; [21](#block-1-0)([13](#block-1-0)):4674. <https://doi.org/10.3390/ijms21134674> PMID: [32630059](http://www.ncbi.nlm.nih.gov/pubmed/32630059)
- [12](#block-1-0). Soles-Tarres I, Cabezas-Llobet N, Vaudry D, Xifro X. Protective effects of pituitary adenylate cyclase-activating polypeptide and vasoactive intestinal peptide against cognitive decline in neurodegenerative diseases. *Front Cell Neurosci*. 2020; 14:[22](#block-1-0)1. <https://doi.org/10.3389/fncel.2020.00221> PMID: [32765225](http://www.ncbi.nlm.nih.gov/pubmed/32765225)
13. Li J, Lu C, Jiang M, Niu X, Guo H, Li L, et al. Traditional chinese medicine-based network pharmacology could lead to new multicomponent drug discovery. *Evid Based Complement Alternat Med*. 2012; 2012:149762. <https://doi.org/10.1155/2012/149762> PMID: [23346189](http://www.ncbi.nlm.nih.gov/pubmed/23346189)
14. Xu J, Qi L, Cheng L, Zhang Y, Xu J, Lou W. Network pharmacology-based study on mechanism of Indigo Naturalis in treatment of primary biliary cirrhosis. *Zhongyi Jiehe Ganbing Zazhi*. 2020; 30(5):52–4, 9, 109.
15. Pan Y, Xu F, Gong H, Wu F-f, Chen L, Zeng Y-l, et al. Network pharmacology-based study on the mechanism of Ganfule in the prevention and treatment of primary liver cancer. *Zhongchengyao*. 2020; 42(12):62–9.
- [16](#block-1-0). Liao J-m, Qin Z-j, Yang Q-y, Li R-q, Xu W-c. Network pharmacology-based study on mechanism of *Spatholobus suberectus* Dunn treating hepatocellular carcinoma. *Guangxi Yixue*. 2020; 42(14):72–7.
- [17](#block-1-0). Zheng C-S, Xu X-J, Ye H-Z, Wu G-W, Li X-H, Xu H-F, et al. Network pharmacology-based prediction of the multi-target capabilities of the compounds in Taohong Siwu decoction, and their application in osteoarthritis. *Exp Ther Med*. 2013; 6(1):1[25](#block-12-0)–32. <https://doi.org/10.3892/etm.2013.1106> PMID: [23935733](http://www.ncbi.nlm.nih.gov/pubmed/23935733)
- [18](#block-1-0). Hong M, Zhang Y, Li S, Tan HY, Wang N, Mu S, et al. A network pharmacology-based study on the hepatoprotective effect of *Fructus Schisandrae*. *Molecules*. 2017; 22(10):16171–11.
- [19](#block-1-0). Fang J, Wang L, Wu T, Yang C, Gao L, Cai H, et al. Network pharmacology-based study on the mechanism of action for herbal medicines in Alzheimer treatment. *Journal of Ethnopharmacology*. 2016; 196:[28](#block-12-0)1–92. <https://doi.org/10.1016/j.jep.2016.11.034> PMID: [27888133](http://www.ncbi.nlm.nih.gov/pubmed/27888133)
20. Luo Y, Patnala S, Shan L, Xu L, Dai Y, Kanfer I, et al. Neuroprotective Effect of Extract-fractions from *Sceletium tortuosum* and their Preliminary Constituents Identification by UPLC-qTOF-MS with Collision Energy and MassFragment Software. *Journal of Pharmaceutical and Biomedical Sciences*. 2021; 11(02):31–46.
21. Patnala S, Kanfer I. Chapter 6—Quality control, extraction methods, and standardization: Interface between traditional use and scientific investigation. In: Henkel R, Agarwal A, editors. *Herbal Medicine in Andrology*: Academic Press; 2021. p. 175–87.
22. Tommonaro G, Garcia-Font N, Vitale RM, Pejin B, Iodice C, Canadas S, et al. Avarol derivatives as competitive AChE inhibitors, non hepatotoxic and neuroprotective agents for Alzheimer's disease. *Eur J Med Chem*. 2016; 122:3[26](#block-12-0)–38. <https://doi.org/10.1016/j.ejmech.2016.06.036> PMID: [27376495](http://www.ncbi.nlm.nih.gov/pubmed/27376495)
- [23](#block-11-0). Takada Y, Yonezawa A, Kume T, Katsuki H, Kaneko S, Sugimoto H, et al. Nicotinic acetylcholine receptor-mediated neuroprotection by donepezil against glutamate neurotoxicity in rat cortical neurons. *J Pharmacol Exp Ther*. 2003; 306(2):772–7. <https://doi.org/10.1124/jpet.103.050104> PMID: [12734391](http://www.ncbi.nlm.nih.gov/pubmed/12734391)
- [24](#block-11-0). Jo S, Yarishkin O, Hwang YJ, Chun YE, Park M, Woo DH, et al. GABA from reactive astrocytes impairs memory in mouse models of Alzheimer's disease. *Nat Med* (N Y, NY, U S). 2014; 20(8):886–96. <https://doi.org/10.1038/nm.3639> PMID: [24973918](http://www.ncbi.nlm.nih.gov/pubmed/24973918)
25. Froestl W, Muhs A, Pfeifer A. Cognitive enhancers (nootropics). Part 2: drugs interacting with enzymes. Update 2014. *J Alzheimers Dis*. 2014; 42(1):1–68. <https://doi.org/10.3233/JAD-140402> PMID: [24903780](http://www.ncbi.nlm.nih.gov/pubmed/24903780)
26. Wilcock GK, Birks J, Whitehead A, Evans SJG. The effect of selegiline in the treatment of people with Alzheimer's disease: a meta-analysis of published trials. *Int J Geriatr Psychiatry*. 2002; 17(2):175–83. <https://doi.org/10.1002/gps.545> PMID: [11813282](http://www.ncbi.nlm.nih.gov/pubmed/11813282)
- [27](#block-12-0). Park J-H, Ju YH, Choi JW, Song HJ, Jang BK, Woo J, et al. Newly developed reversible MAO-B inhibitor circumvents the shortcomings of irreversible inhibitors in Alzheimer's disease. *Sci Adv*. 2019; 5(3): eaav0316. <https://doi.org/10.1126/sciadv.aav0316> PMID: [30906861](http://www.ncbi.nlm.nih.gov/pubmed/30906861)
28. Dimpfel W, Schombert L, Gericke N. Electropharmacogram of *Sceletium tortuosum* extract based on spectral local field power in conscious freely moving rats. *J Ethnopharmacol*. 2016; 177:140–7. <https://doi.org/10.1016/j.jep.2015.11.036> PMID: [26608705](http://www.ncbi.nlm.nih.gov/pubmed/26608705)
29. Schell R. *Sceletium tortuosum* and Mesembrine: A Potential Alternative Treatment for Depression. United States of America: Scripps College; 2014.
30. Dimpfel W, Gericke N, Suliman S, Dipah GNC. Psychophysiological effects of zembrin using quantitative EEG source density in combination with eye-tracking in 60 healthy subjects. A double-blind, randomized, placebo-controlled, 3-armed study with parallel design. *Neurosci Med*. 2016; 7(3):114–32.

{19}------------------------------------------------

31. Dimpfel W, Gericke N, Suliman S, Dipah GNC. Effect of Zembrin on brain electrical activity in 60 older subjects after 6 weeks of daily intake. A prospective, randomized, double-blind, placebo-controlled, 3-armed study in a parallel design. *World J Neurosci.* 2017; 7(1):1[40](#block-4-0)–71.
32. Carpenter JM, Ali Z, Abe N, Khan IA, Jourdan MK, Fountain EM, et al. The effects of *Sceletium tortuosum* (L.) N.E. Br. extract fraction in the chick anxiety-depression model. *J Ethnopharmacol.* 2016; 193:329–32. <https://doi.org/10.1016/j.jep.2016.08.019> PMID: [27553978](http://www.ncbi.nlm.nih.gov/pubmed/27553978)
- [33](#block-1-0). Terburg D, Syal S, Rosenberger LA, Heany S, Phillips N, Gericke N, et al. Acute Effects of *Sceletium tortuosum* (Zembrin), a Dual 5-HT Reuptake and PDE4 Inhibitor, in the Human Amygdala and its Connection to the Hypothalamus. *Neuropsychopharmacology.* 2013; [38](#block-3-0)(13):2708–16. <https://doi.org/10.1038/npp.2013.183> PMID: [23903032](http://www.ncbi.nlm.nih.gov/pubmed/23903032)
- [34](#block-1-0). Singh A, Verma P, Raju A, Mohanakumar KP. Nimodipine attenuates the parkinsonian neurotoxin, MPTP-induced changes in the calcium binding proteins, calpain and calbindin. *J Chem Neuroanat.* 2019; 95:89–94. <https://doi.org/10.1016/j.jchemneu.2018.02.001> PMID: [29427747](http://www.ncbi.nlm.nih.gov/pubmed/29427747)
35. Kupsch A, Gerlach M, Pupeter SC, Sautter J, Dirr A, Arnold G, et al. Pretreatment with nimodipine prevents MPTP-induced neurotoxicity at the nigral, but not at the striatal level in mice. *NeuroReport.* 1995; 6(4):621–5. <https://doi.org/10.1097/00001756-199503000-00009> PMID: [7605913](http://www.ncbi.nlm.nih.gov/pubmed/7605913)
- [36](#block-1-0). Ota H, Ogawa S, Ouchi Y, Akishita M. Protective effects of NMDA receptor antagonist, memantine, against senescence of PC12 cells: A possible role of nNOS and combined effects with donepezil. *Exp Gerontol.* 2015; 72:109–16. <https://doi.org/10.1016/j.exger.2015.09.016> PMID: [26408226](http://www.ncbi.nlm.nih.gov/pubmed/26408226)
- [37](#block-3-0). Ellman GL, Courtney KD, Andres V Jr., Featherstone RM. A new and rapid colorimetric determination of acetylcholinesterase activity. *Biochem Pharmacol.* 1961; 7:88–95. [https://doi.org/10.1016/0006-2952\(61\)90145-9](https://doi.org/10.1016/0006-2952(61)90145-9) PMID: [13726518](http://www.ncbi.nlm.nih.gov/pubmed/13726518)
38. Orhan I, Sener B, Choudhary MI, Khalid A. Acetylcholinesterase and butyrylcholinesterase inhibitory activity of some Turkish medicinal plants. *J Ethnopharmacol.* 2004; 91(1):57–60. <https://doi.org/10.1016/j.jep.2003.11.016> PMID: [15036468](http://www.ncbi.nlm.nih.gov/pubmed/15036468)
- [39](#block-3-0). Holt A, Sharman DF, Baker GB, Palcic MM. A continuous spectrophotometric assay for monoamine oxidase and related enzymes in tissue homogenates. *Anal Biochem.* 1997; 2[44](#block-4-0)(2):384–92. <https://doi.org/10.1006/abio.1996.9911> PMID: [9025956](http://www.ncbi.nlm.nih.gov/pubmed/9025956)
40. Awale M, Reymond J-L. Polypharmacology Browser PPB2: Target Prediction Combining Nearest Neighbors with Machine Learning. *J Chem Inf Model.* 2019; 59(1):10–7. <https://doi.org/10.1021/acs.jcim.8b00524> PMID: [30558418](http://www.ncbi.nlm.nih.gov/pubmed/30558418)
- [41](#block-4-0). Stelzer G, Rosen N, Plaschkes I, Zimmerman S, Twik M, Fishilevich S, et al. The GeneCards Suite: From Gene Data Mining to Disease Genome Sequence Analyses. *Curr Protoc Bioinformatics.* 2016; 54:1.30.1–1.3. <https://doi.org/10.1002/cpbi.5> PMID: [27322403](http://www.ncbi.nlm.nih.gov/pubmed/27322403)
- [42](#block-4-0). Pinero J, Ramirez-Anguita JM, Sauch-Pitarch J, Ronzano F, Centeno E, Sanz F, et al. The DisGeNET knowledge platform for disease genomics: 2019 update. *Nucleic Acids Res.* 2020; 48(D1):D8[45](#block-6-0)–D55. <https://doi.org/10.1093/nar/gkz1021> PMID: [31680165](http://www.ncbi.nlm.nih.gov/pubmed/31680165)
- [43](#block-4-0). Szklarczyk D, Gable AL, Lyon D, Junge A, Wyder S, Huerta-Cepas J, et al. STRING v11: protein-protein association networks with increased coverage supporting functional discovery in genome-wide experimental datasets. *Nucleic Acids Res.* 2019; [47](#block-11-0)(D1):D607–D13. <https://doi.org/10.1093/nar/gky1131> PMID: [30476243](http://www.ncbi.nlm.nih.gov/pubmed/30476243)
44. Huang DW, Sherman BT, Lempicki RA. Systematic and integrative analysis of large gene lists using DAVID bioinformatics resources. *Nat Protoc.* 2009; 4(1):44–57. <https://doi.org/10.1038/nprot.2008.211> PMID: [19131956](http://www.ncbi.nlm.nih.gov/pubmed/19131956)
45. Stafford GI, Pedersen PD, Jäger AK, Staden JV. Monoamine oxidase inhibition by southern African traditional medicinal plants. *South African Journal of Botany.* 2007; 73(3):384–90.
- [46](#block-11-0). Kapewangolo P, Tawha T, Nawinda T, Knott M, Hans R. *Sceletium tortuosum* demonstrates in vitro anti-HIV and free radical scavenging activity. *South African Journal of Botany.* 2016; 106:140–3.
47. Gonzalez-Burgos E, Liaudanskas M, Viskelis J, Zvikas V, Janulis V, Gomez-Serranillos MP. Antioxidant activity, neuroprotective properties and bioactive constituents analysis of varying polarity extracts from *Eucalyptus globulus* leaves. *J Food Drug Anal.* 2018; 26(4):1293–302. <https://doi.org/10.1016/j.jfda.2018.05.010> PMID: [30249328](http://www.ncbi.nlm.nih.gov/pubmed/30249328)
48. Ren Z, Zhang R, Li Y, Li Y, Yang Z, Yang H. Ferulic acid exerts neuroprotective effects against cerebral ischemia/reperfusion-induced injury via antioxidant and anti-apoptotic mechanisms in vitro and in vivo. *Int J Mol Med.* 2017; 40(5):1444–56. <https://doi.org/10.3892/ijmm.2017.3127> PMID: [28901374](http://www.ncbi.nlm.nih.gov/pubmed/28901374)
- [49](#block-11-0). Yousef AOS, Fahad AA, Abdel Moneim AE, Metwally DM, El-Khadragy MF, Kassab RB. The neuroprotective role of coenzyme Q10 against lead acetate-induced neurotoxicity is mediated by antioxidant, anti-inflammatory and anti-apoptotic activities. *Int J Environ Res Public Health.* 2019; 16(16):2895.

{20}------------------------------------------------

- [50](#block-11-0). Coetzee DD, Lopez V, Smith C. High-mesembrine *Sceletium* extract (Trimesemine®) is a monoamine releasing agent, rather than only a selective serotonin reuptake inhibitor. *J Ethnopharmacol.* 2016; 177:111–6. <https://doi.org/10.1016/j.jep.2015.11.034> PMID: [26615766](http://www.ncbi.nlm.nih.gov/pubmed/26615766)
- [51](#block-11-0). Yue W, Li Y, Zhang T, Jiang M, Qian Y, Zhang M, et al. ESC-derived basal forebrain cholinergic neurons ameliorate the cognitive symptoms associated with Alzheimer's disease in mouse models. *Stem Cell Rep.* 2015; 5(5):776–90. <https://doi.org/10.1016/j.stemcr.2015.09.010> PMID: [26489896](http://www.ncbi.nlm.nih.gov/pubmed/26489896)
- [52](#block-11-0). Inestrosa NC, Dinamarca MC, Alvarez A. Amyloid-cholinesterase interactions. Implications for Alzheimer's disease. *FEBS J.* 2008; 275(4):625–32. <https://doi.org/10.1111/j.1742-4658.2007.06238.x> PMID: [18205831](http://www.ncbi.nlm.nih.gov/pubmed/18205831)
- [53](#block-11-0). Spinks A, Wasiak J. Scopolamine (hyoscine) for preventing and treating motion sickness. *Cochrane database of systematic reviews.* 2011(6). <https://doi.org/10.1002/14651858.CD002851.pub4> PMID: [21678338](http://www.ncbi.nlm.nih.gov/pubmed/21678338)
- [54](#block-11-0). Ben-Barak J, Dudai Y. Scopolamine induces an increase in muscarinic receptor level in rat hippocampus. *Brain Res.* 1980; 193(1):309–13. [https://doi.org/10.1016/0006-8993\(80\)90973-7](https://doi.org/10.1016/0006-8993(80)90973-7) PMID: [7378826](http://www.ncbi.nlm.nih.gov/pubmed/7378826)
- [55](#block-11-0). Naoi M, Riederer P, Maruyama W. Modulation of monoamine oxidase (MAO) expression in neuropsychiatric disorders- genetic and environmental factors involved in type A MAO expression. *J Neural Transm.* 2016; 123(2):91–106. <https://doi.org/10.1007/s00702-014-1362-4> PMID: [25604428](http://www.ncbi.nlm.nih.gov/pubmed/25604428)
- [56](#block-11-0). Youdim MBH, Bakhle YS. Monoamine oxidase: isoforms and inhibitors in Parkinson's disease and depressive illness. *Br J Pharmacol.* 2006; 147(Suppl. 1):S287–S96. <https://doi.org/10.1038/sj.bjp.0706464> PMID: [16402116](http://www.ncbi.nlm.nih.gov/pubmed/16402116)
- [57](#block-12-0). Dimpfel W, Franklin R, Gericke N, Schombert L. Effect of Zembrin(®) and four of its alkaloid constituents on electric excitability of the rat hippocampus. *J Ethnopharmacol.* 2018; 223:135–41. <https://doi.org/10.1016/j.jep.2018.05.010> PMID: [29758341](http://www.ncbi.nlm.nih.gov/pubmed/29758341)
- [58](#block-15-0). Harvey AL, Young LC, Viljoen AM, Gericke NP. Pharmacological actions of the South African medicinal and functional food plant *Sceletium tortuosum* and its principal alkaloids. *J Ethnopharmacol.* 2011; 137(3):1124–9. <https://doi.org/10.1016/j.jep.2011.07.035> PMID: [21798331](http://www.ncbi.nlm.nih.gov/pubmed/21798331)