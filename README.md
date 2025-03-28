# ChainNet

**There are three ways to access the ChainNet data:**
1. By downloading [this JSON file](https://raw.githubusercontent.com/rowanhm/ChainNet/main/data/chainnet.json). 
This file contains all of ChainNet is one place. 
Details of its structure are given below. 
2. By downloading one of three simplified versions, which contain only [metaphor](https://raw.githubusercontent.com/rowanhm/ChainNet/main/data/chainnet_simple/chainnet_metaphor.json), [metonymy](https://raw.githubusercontent.com/rowanhm/ChainNet/main/data/chainnet_simple/chainnet_metonymy.json), or [homonymy](https://raw.githubusercontent.com/rowanhm/ChainNet/main/data/chainnet_simple/chainnet_homonymy.json).
These simplified versions exclude split and virtual senses, and have been designed to make it easy to access all of the examples of each phenomena without having to extract them yourselves. 
3. By looking at [this automatically-generated PDF](https://rowanhm.github.io/ChainNet/documentation/ChainNet_Data.pdf), which includes a graphical representation of each word in ChainNet, but does not include the feature transformations.
It can be useful if you want to reference the ChainNet annotation quickly for a word.

In Python, JSON files can be opened trivially using the `json` library, e.g.
```angular2html
import json

with open("data/chainnet.json", "r") as fp:
    chainnet = json.load(fp)
```

Any work that uses should ChainNet should cite [our LREC-COLING paper](https://aclanthology.org/2024.lrec-main.266/):
```angular2html
@inproceedings{maudslay-etal-2024-chainnet-structured,
    title = "{C}hain{N}et: Structured Metaphor and Metonymy in {W}ord{N}et",
    author = "Maudslay, Rowan Hall  and Teufel, Simone  and Bond, Francis  and Pustejovsky, James",
    editor = "Calzolari, Nicoletta  and Kan, Min-Yen  and Hoste, Veronique  and Lenci, Alessandro  and Sakti, Sakriani and Xue, Nianwen",
    booktitle = "Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation (LREC-COLING 2024)",
    month = may,
    year = "2024",
    address = "Torino, Italy",
    publisher = "ELRA and ICCL",
    url = "https://aclanthology.org/2024.lrec-main.266",
    pages = "2984--2996"
}
```

If you notice any mistakes in the data, or have suggestions for future versions, please get in touch.

## Data Format

The ChainNet JSON is a dict with two entries, `metadata` and `content`.
The `content` entry contains a list with 6500 entries, where each entry corresponds to the annotation for a word. 
Each word is a dictionary, with the following keys:
* `wordform` The word string.
* `annotator_id` The unique ID of the annotator who produced the annotation.
* `is_known` Flag indicating whether the annotator knew the word.
* `annotation_seconds` The time the annotator spent in the interface producing this annotation.
* `senses` A list of the senses in the annotation.

Each sense is a dictionary which has the following keys:

* `sense_id` The index of the sense of the word.
* `wordform` The word string of the sense. Usually all senses have the same wordform, but they sometimes differ in terms of capitalisation.
* `definition` The WordNet definition of the sense. Synonyms are in square brackets at the start, followed by a description, and then sometimes example usages.
* `wordnet_sense_id` The WordNet 3.0 sense ID (called 'lemma' in NLTK), e.g. "almanac%1:10:01::". If the sense is a virtual sense, it will not have a corresponding sense in WordNet, and this will be null. If a sense is a split sense, then another sense will have the same WordNet ID. 
* `wordnet_synset_id` The WordNet 3.0 synset ID, e.g. "almanac.n.01". If the sense is a virtual sense, it will not have a corresponding synset in WordNet, and this will be null.
* `label` The label the annotator assigned to the sense (either "prototype", "metaphor", or "metonymy").
* `child_of` The index of the sense which this sense extends (if it is a metaphor or a metonym).
* `is_known` Flag indicating whether the annotator knew this particular sense of the word.
* `is_virtual` Flag indicating whether this sense is a virtual sense.
* `is_split` Flag indicating whether this sense is one half of a split sense.
* `features` A list of the features belonging to the word.

Finally, each feature is a dictionary has the following keys:

* `feature_id` An automatically-generated unique ID given to each feature.
* `feature_string` The string of the feature, e.g. "is big". This excludes the prompt fragment which elicited the feature ("This thing ___").
* `label` Whether the feature is a new feature, a kept feature, a lost feature, or a modified feature.
* `source_feature_id` The unique ID of the feature which is being edited (if this feature is kept/lost/modified).
* `source_feature_string` The string the feature which is being edited.

## Mistakes

If you spot a mistake, please let us know by submitting an issue.
Alternatively, you can fix this mistake yourself and submit a pull request.
This can be achieved by editing the `chainnet_edges.tsv` and (optionally) the `chainnet_virtuals.tsv` files in `data/working_files`.
After making an edit, run `python/u4_updating/s2_sanity_check.py` to check that the edit is not malformed.
Afterwards, run `python/u4_updating/s3_generate_json.py`.
This regenerates the working version of the ChainNet `json` file, which can be found in `data/working_files`.
We will periodically update the main file with this working version, when there have been enough updates.


## Reproduction

This repository has five key folders:
* `bin` Temporary files.
* `data` Prerequisite data needed for processing, as well as the ChainNet data.
* `documentation` ChainNet documents. 
* `javascript` Code for the annotation collection interface.
* `python` Code for annotation collection preprocessing, data analysis, and polysemy parsing.

This code was tested using Python version 3.11.4. 
To run our code, please set up a virtual environment and install the necessary libraries using `python -r requirements.txt`.
After this, in Python run `import nltk; nltk.download('wordnet')` to install WordNet 3.0.
Run all code from the root directory.

The processing work is divided into three stages, which follow from each other sequentially.
All of the critical files that are produced by each stage are included in this repository.
Because of this, each stage can be reproduced independently.

### Annotation Collection

The annotation guidelines are provided [here](https://rowanhm.github.io/ChainNet/documentation/ChainNet_Annotation_Guidelines.pdf).
These guidelines were written for non-expert annotators.
Because of this, we referred to prototypes as "core senses" and metonymies as "associations".
We also used "conduit senses" to bias annotators towards simpler annotations.
This is explained in the paper.

The three JSON files that are needed by the annotation interface are provided in `bin`. 
If you wish to recreate them, you can run stages one through four in `python/u1_collection`.
To do this you will need to download and decompress the Princeton GlossTag Corpus from [here](https://wordnetcode.princeton.edu/glosstag-files/WordNet-3.0-glosstag.zip) and put it into `data/collection`.

With these files setup, you can run the interface locally using `index.html`.
You can also access the interface [here](https://rowanhm.github.io/ChainNet/).
The interface uses a private Google Firebase backend for data storage and to manage access.
If you wish to use the interface to collect your own data, you will need to set up your own Realtime Database in Google Firebase, and adapt the relevant details in `javascript/io.js`.

Annotation was collected in queues of 10 words, which were generated by sampling words according to their frequency.
The queues we used are provided in `data/collection/queues.json`.
You can add additional queues to this to collect annotation for other words.

From Google Firebase, the saved data can be exported as a JSON and put into `bin/collection`. 
This data can then be extracted using `python/u1_collection/s5_data_extractor.py`.

### Data Analysis

The analysis code is found in `python/u2_analysis`.
Run `s1_agreement.py` to recreate the agreement results.
This prints the latex tables found in the paper.
The rest of the files produce the other statistics found in the paper, and process the ChainNet annotation into the JSON files that are released.
To run the homonymy analysis, you will need to put the file `within_pos_clusters.csv` from [here](https://github.com/rowanhm/wordnet-homonymy) into `data/analysis`.

### Polysemy Parsing

To run the polysemy parsing code, please first download the SensEmBert embeddings into `data/parsing` and unpack them. 

> :warning: **At the time of writing (10/05/24), the SensEmBert website appears to have been infiltrated.** Historically, the embeddings could be downloaded [here](http://sensembert.org/resources/sensembert_data.tar.gz) (access with care).

After the embeddings are downloaded, run stages one and two in `python/u3_parsing` to initialise the data for training.
You will need to have first run `python/u2_analysis/build_chainnet.py`, to build the necessary ChainNet version.
If you want to recreate the results found in the paper, download the model checkpoints from [here](https://drive.google.com/file/d/15y1mFN7LykFIqBLkcBgUL1y4i28cTWMX/view?usp=sharing), put them in `bin/parsing/models`, then run stages four onwards in `python/u3_parsing`.
