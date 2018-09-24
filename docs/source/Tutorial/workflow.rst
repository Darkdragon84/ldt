=============================
The overall idea and workflow
=============================

---------------------------------------------
I want to use LDT to evaluate word embeddings
---------------------------------------------

The core of LD methodology is large-scale automatic annotation of relations in word vector neighborhoods. You get your embeddings, you get the vocabulary sample that you want to investigate (or take ours for comparison), and you retrieve *n* neighbor pairs for those words. Then LDT can be used to annotate the files, and the resulting statistics will hopefully tell you what your embedding model is actually doing.

The overall algorithm for initial processing of input words is as follows:

.. figure:: /_static/ldt_full_workflow.png
   :align: center

Section :ref:`Collecting all linguistic information about a word` and section :ref:`Detecting relations in pairs of words` describe how LDT aggregates information from various linguistic resources to achieve automatic annotation of all possible relations in word pairs. Section :ref:`Linguistic resources in LDT` of the tutorial describes the various linguistic resources that you can use and configure in this process.


---------------------------------------------------------------------
I don't care about word embeddings, just show me the new dictionaries
---------------------------------------------------------------------

Head over to section :ref:`Linguistic resources in LDT`. A few quick highlights of what LDT can do for you:

Querying WordNet, Wiktionary, Wiktionary Thesaurus and BabelNet:

>>> wikisaurus.get_relations("cat", relations="all")
{'synonyms': ['tabby', 'puss', 'cat', 'kitty', 'moggy', 'housecat', 'malkin', 'kitten', 'tom', 'grimalkin', 'pussy-cat', 'mouser', 'pussy', 'queen', 'tomcat', 'mog'],
 'hyponyms': [],
 'hypernyms': ['mammal', 'carnivore', 'vertebrate', 'feline', 'animal', 'creature'],
 'antonyms': [],
 'meronyms': []}
>>> wiktionary.get_relations("white", relations=["synonyms"])
['pale', 'fair']
>>> babelnet.get_relations("senator", relations=["hypernyms"])
{'hypernyms': ['legislative_assembly', 'metropolitan_see_of_milan', 'poltician', 'legislative_seat', 'senator_of_rome', 'band', 'the_upper_house', 'polictian', 'patres_conscripti', 'musical_ensemble', 'presbytery', 'politician', 'pol', 'solo_project', 'policymaker', 'political_figure', 'politican', 'policymakers', 'archbishop_emeritus_of_milan', 'deliberative_assemblies', 'ensemble', 'career_politics', 'soloproject', 'list_of_musical_ensembles', 'legislative', 'roman_senators', 'archbishopric_of_milan', 'politicain', 'rock_bands', 'section_leader', 'musical_organisation', 'music_band', 'four-piece', 'roman_catholic_archdiocese_of_milan', 'upper_house', 'archdiocese_of_milan', 'band_man', 'milanese_apostolic_catholic_church', 'legistrative_branch', 'group', 'solo-project', 'music_ensemble', 'law-makers', 'roman_senator', 'legislative_arm_of_government', 'solo_act', 'patronage', 'roman_catholic_archbishop_of_milan', 'bar_band', 'senate_of_rome', 'deliberative_body', 'see_of_milan', 'legislative_fiat', 'musical_group', 'ambrosian_catholic_church', 'legislature_of_orissa', 'legislative_branch_of_government', 'list_of_politicians', 'senatorial_lieutenant', 'roman_catholic_archdiocese_of_milano', 'legislature_of_odisha', 'bandmember', 'assembly', 'archdiocese_of_milano', 'bishop_of_milan', 'ensemble_music', 'solo_musician', 'musical_duo', 'legislative_branch_of_goverment', 'first_chamber', 'politicians', 'legislative_bodies', 'political_leaders', 'politico', 'music_group', 'legislative_body', 'career_politician', 'legislature', 'rock_group', 'legislative_power', 'diocese_of_milan', 'musical_ensembles', 'musical_organization', 'revising_chamber', 'archbishops_of_milan', 'political_leader', 'deliberative_assembly', 'conscript_fathers', 'five-piece', 'catholic_archdiocese_of_milan', 'pop_rock_band', 'senatrix', 'deliberative_organ', 'polit.', 'roman_senate', 'legislative_politics', 'bishopric_of_milan', 'legislative_branch', 'musical_band', 'archbishop_of_milan', 'legislatures', 'general_assembly', 'musical_groups', 'instrumental_ensemble', 'politition', 'patres', 'upper_chamber', 'solo-act', 'conscripti', 'legislator']}

Derivational analysis:

>>> derivation_dict.analyze("kindness")
{'original_word': ['kindness'],
 'other': [],
  'prefixes': [],
  'related_words': ['kindhearted', 'kindly', 'in kind', 'kindliness', 'kinda', 'many-kinded', 'first-of-its-kind', 'kind of', 'kindful', 'kindless'],
  'roots': ['kind'],
  'suffixes': ['-ness']}

Lemmatization with productive rules and Wiktionary/BabelNet:

>>> morph_metadict.lemmatize("GPUs")
['GPU']

Trustworthy correction of frequent misspelling patterns:

>>> spellchecker_en.spelling_nazi("abritrary")
'arbitrary'
