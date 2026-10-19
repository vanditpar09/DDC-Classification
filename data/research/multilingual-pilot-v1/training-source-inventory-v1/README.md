# PDFs used for the current model

The saved `native_silver_v2` fitting record traces to **68 PDF files across 34 native-language editions**. These are the sources of selected OCR passages, not whole-book training inputs.

The full fitting run used 3,061 catalog metadata records plus 53 native editions (49 work groups, 156 passages). The other 19 native editions used publisher text with no PDF passage provenance.

## Find the files

Paths below are relative to the repository root. These links work in the local checkout; original PDFs are ignored by Git and absent from a fresh clone. The JSON inventory includes all source PDFs, hashes, page numbers, passage paths, source URLs where receipts exist, and saved partition membership.

[Full inventory](inventory.json). Regenerate locally with `python3 scripts/inventory_training_pdfs.py`.

Most files are under `../acquisition-v1/books/` through `../acquisition-v4/books/`. NCERT often supplies separate chapter PDFs. File counts therefore do not equal book counts.

## Fitting PDF sources

| Book | Language | Source PDF | Sampled PDF pages |
|---|---|---|---|
| डिटेक्टिव्ह अल्फा आणि रत्नजडित खंजिराचे रहस्य | mar | [acquisition-v1/books/detective_alpha_saurabh_wagale.pdf](../acquisition-v1/books/detective_alpha_saurabh_wagale.pdf) | 23, 46, 70 |
| फुल्लारी | mar | [acquisition-v1/books/fullari_vinita_deshpande.pdf](../acquisition-v1/books/fullari_vinita_deshpande.pdf) | 20, 40, 61 |
| मुन्नी | mar | [acquisition-v1/books/munni_aruna_sabane.pdf](../acquisition-v1/books/munni_aruna_sabane.pdf) | 82, 164, 245 |
| நன்னூல் | tam | [acquisition-v1/books/pm0147.pdf](../acquisition-v1/books/pm0147.pdf) | 9, 18, 27 |
| गुप्तहेर सत्यवीर आणि भूतबंगल्याचे रहस्य | mar | [acquisition-v2/books/bhoot_bangalyache_rahasya_akshay_jadhav.pdf](../acquisition-v2/books/bhoot_bangalyache_rahasya_akshay_jadhav.pdf) | 30, 61, 92 |
| युरोप-कवडसे | mar | [acquisition-v2/books/europe_kavadse_maneesha_dikshit.pdf](../acquisition-v2/books/europe_kavadse_maneesha_dikshit.pdf) | 32, 64, 96 |
| इब्लिस | mar | [acquisition-v2/books/iblis_suraj_gatade.pdf](../acquisition-v2/books/iblis_suraj_gatade.pdf) | 115, 230, 345 |
| रंग ईशान्येचे | mar | [acquisition-v2/books/ishany_bharat_neelima_kulkarni.pdf](../acquisition-v2/books/ishany_bharat_neelima_kulkarni.pdf) | 30 |
| दक्षिण केरळ अर्थात कोची – मुन्नार – तेक्कडी – आलप्पुळा | mar | [acquisition-v2/books/keral_shailesh_purohit.pdf](../acquisition-v2/books/keral_shailesh_purohit.pdf) | 16, 33, 50 |
| डिटेक्टिव्ह अल्फा आणि अर्धप्रकाशित खिडकी | mar | [acquisition-v2/books/khidkee_saurabh_wagle.pdf](../acquisition-v2/books/khidkee_saurabh_wagle.pdf) | 41, 82, 124 |
| मात | mar | [acquisition-v2/books/maaat_ketakee_shah.pdf](../acquisition-v2/books/maaat_ketakee_shah.pdf) | 22, 45, 68 |
| मला भावलेला कॅनडा | mar | [acquisition-v2/books/mb_canada_bb_desai.pdf](../acquisition-v2/books/mb_canada_bb_desai.pdf) | 33, 66, 98 |
| ओमेगा अपग्रेडेड | mar | [acquisition-v2/books/omega_upgraded_abhishek_thamke.pdf](../acquisition-v2/books/omega_upgraded_abhishek_thamke.pdf) | 58, 116, 174 |
| परिमार्जन | mar | [acquisition-v2/books/parimarjan_sudhir_karkhanis.pdf](../acquisition-v2/books/parimarjan_sudhir_karkhanis.pdf) | 24, 48, 71 |
| पिंजरा | mar | [acquisition-v2/books/pinjaraa_sanjay_bansode.pdf](../acquisition-v2/books/pinjaraa_sanjay_bansode.pdf) | 14, 28, 41 |
| வேளிர் வரலாறு | tam | [acquisition-v2/books/pm0413.pdf](../acquisition-v2/books/pm0413.pdf) | 48, 71 |
| நெற்றிக் கண் (2 பாகங்களாக) | tam | [acquisition-v2/books/pm0839.pdf](../acquisition-v2/books/pm0839.pdf) | 49, 98, 147 |
| Jigyasa | hin | [acquisition-v3/books/fhcu1/fhcu101.pdf](../acquisition-v3/books/fhcu1/fhcu101.pdf) | 4 |
| Jigyasa | hin | [acquisition-v3/books/fhcu1/fhcu106.pdf](../acquisition-v3/books/fhcu1/fhcu106.pdf) | 10 |
| Jigyasa | hin | [acquisition-v3/books/fhcu1/fhcu112.pdf](../acquisition-v3/books/fhcu1/fhcu112.pdf) | 12 |
| Curiosity (Marathi) | mar | [acquisition-v3/books/fmrcu1/fmrcu101.pdf](../acquisition-v3/books/fmrcu1/fmrcu101.pdf) | 4 |
| Curiosity (Marathi) | mar | [acquisition-v3/books/fmrcu1/fmrcu106.pdf](../acquisition-v3/books/fmrcu1/fmrcu106.pdf) | 11 |
| Curiosity (Marathi) | mar | [acquisition-v3/books/fmrcu1/fmrcu112.pdf](../acquisition-v3/books/fmrcu1/fmrcu112.pdf) | 12 |
| Curiosity (Tamil) | tam | [acquisition-v3/books/ftmcu1/ftmcu101.pdf](../acquisition-v3/books/ftmcu1/ftmcu101.pdf) | 4 |
| Curiosity (Tamil) | tam | [acquisition-v3/books/ftmcu1/ftmcu106.pdf](../acquisition-v3/books/ftmcu1/ftmcu106.pdf) | 11 |
| Curiosity (Tamil) | tam | [acquisition-v3/books/ftmcu1/ftmcu112.pdf](../acquisition-v3/books/ftmcu1/ftmcu112.pdf) | 12 |
| Ganita Prakash Part-I (Hindi) | hin | [acquisition-v3/books/hhgp1/hhgp101.pdf](../acquisition-v3/books/hhgp1/hhgp101.pdf) | 9 |
| Ganita Prakash Part-I (Hindi) | hin | [acquisition-v3/books/hhgp1/hhgp103.pdf](../acquisition-v3/books/hhgp1/hhgp103.pdf) | 17 |
| Ganita Prakash Part-I (Hindi) | hin | [acquisition-v3/books/hhgp1/hhgp107.pdf](../acquisition-v3/books/hhgp1/hhgp107.pdf) | 11 |
| Ganita Prakash Part-I (Marathi) | mar | [acquisition-v3/books/hmrgp1/hmrgp101.pdf](../acquisition-v3/books/hmrgp1/hmrgp101.pdf) | 9 |
| Ganita Prakash Part-I (Marathi) | mar | [acquisition-v3/books/hmrgp1/hmrgp103.pdf](../acquisition-v3/books/hmrgp1/hmrgp103.pdf) | 17 |
| Ganita Prakash Part-I (Marathi) | mar | [acquisition-v3/books/hmrgp1/hmrgp107.pdf](../acquisition-v3/books/hmrgp1/hmrgp107.pdf) | 11 |
| Ganita Prakash Part-I (Tamil) | tam | [acquisition-v3/books/htmgp1/htmgp101.pdf](../acquisition-v3/books/htmgp1/htmgp101.pdf) | 9 |
| Ganita Prakash Part-I (Tamil) | tam | [acquisition-v3/books/htmgp1/htmgp103.pdf](../acquisition-v3/books/htmgp1/htmgp103.pdf) | 17 |
| Ganita Prakash Part-I (Tamil) | tam | [acquisition-v3/books/htmgp1/htmgp107.pdf](../acquisition-v3/books/htmgp1/htmgp107.pdf) | 11 |
| Lekhashastra-I | hin | [acquisition-v3/books/khac1/khac101.pdf](../acquisition-v3/books/khac1/khac101.pdf) | 12 |
| Lekhashastra-I | hin | [acquisition-v3/books/khac1/khac103.pdf](../acquisition-v3/books/khac1/khac103.pdf) | 28 |
| Lekhashastra-I | hin | [acquisition-v3/books/khac1/khac107.pdf](../acquisition-v3/books/khac1/khac107.pdf) | 28 |
| Jeev Vigyan | hin | [acquisition-v3/books/khbo1/khbo101.pdf](../acquisition-v3/books/khbo1/khbo101.pdf) | 4 |
| Jeev Vigyan | hin | [acquisition-v3/books/khbo1/khbo109.pdf](../acquisition-v3/books/khbo1/khbo109.pdf) | 8 |
| Jeev Vigyan | hin | [acquisition-v3/books/khbo1/khbo119.pdf](../acquisition-v3/books/khbo1/khbo119.pdf) | 7 |
| Rasayan Vigyan bhag-I | hin | [acquisition-v3/books/khch1/khch101.pdf](../acquisition-v3/books/khch1/khch101.pdf) | 14 |
| Rasayan Vigyan bhag-I | hin | [acquisition-v3/books/khch1/khch103.pdf](../acquisition-v3/books/khch1/khch103.pdf) | 14 |
| Rasayan Vigyan bhag-I | hin | [acquisition-v3/books/khch1/khch106.pdf](../acquisition-v3/books/khch1/khch106.pdf) | 23 |
| Bhartiya Airthryavstha Ka Vikas | hin | [acquisition-v3/books/khec1/khec101.pdf](../acquisition-v3/books/khec1/khec101.pdf) | 8 |
| Bhartiya Airthryavstha Ka Vikas | hin | [acquisition-v3/books/khec1/khec104.pdf](../acquisition-v3/books/khec1/khec104.pdf) | 10 |
| Bhartiya Airthryavstha Ka Vikas | hin | [acquisition-v3/books/khec1/khec108.pdf](../acquisition-v3/books/khec1/khec108.pdf) | 10 |
| Bhartiya Kala ka parichay | hin | [acquisition-v3/books/khfa1/khfa101.pdf](../acquisition-v3/books/khfa1/khfa101.pdf) | 4 |
| Bhartiya Kala ka parichay | hin | [acquisition-v3/books/khfa1/khfa104.pdf](../acquisition-v3/books/khfa1/khfa104.pdf) | 17 |
| Bhartiya Kala ka parichay | hin | [acquisition-v3/books/khfa1/khfa108.pdf](../acquisition-v3/books/khfa1/khfa108.pdf) | 12 |
| Bhautiki-I | hin | [acquisition-v3/books/khph1/khph101.pdf](../acquisition-v3/books/khph1/khph101.pdf) | 6 |
| Bhautiki-I | hin | [acquisition-v3/books/khph1/khph103.pdf](../acquisition-v3/books/khph1/khph103.pdf) | 11 |
| Bhautiki-I | hin | [acquisition-v3/books/khph1/khph107.pdf](../acquisition-v3/books/khph1/khph107.pdf) | 9 |
| Raajneeti Sidhant | hin | [acquisition-v3/books/khps1/khps101.pdf](../acquisition-v3/books/khps1/khps101.pdf) | 8 |
| Raajneeti Sidhant | hin | [acquisition-v3/books/khps1/khps104.pdf](../acquisition-v3/books/khps1/khps104.pdf) | 6 |
| Raajneeti Sidhant | hin | [acquisition-v3/books/khps1/khps108.pdf](../acquisition-v3/books/khps1/khps108.pdf) | 10 |
| Manovigyan | hin | [acquisition-v3/books/khpy1/khpy101.pdf](../acquisition-v3/books/khpy1/khpy101.pdf) | 10 |
| Manovigyan | hin | [acquisition-v3/books/khpy1/khpy104.pdf](../acquisition-v3/books/khpy1/khpy104.pdf) | 9 |
| Manovigyan | hin | [acquisition-v3/books/khpy1/khpy108.pdf](../acquisition-v3/books/khpy1/khpy108.pdf) | 6 |
| Samaj Shastra Parichay-I | hin | [acquisition-v3/books/khsy1/khsy101.pdf](../acquisition-v3/books/khsy1/khsy101.pdf) | 13 |
| Samaj Shastra Parichay-I | hin | [acquisition-v3/books/khsy1/khsy102.pdf](../acquisition-v3/books/khsy1/khsy102.pdf) | 10 |
| Samaj Shastra Parichay-I | hin | [acquisition-v3/books/khsy1/khsy105.pdf](../acquisition-v3/books/khsy1/khsy105.pdf) | 12 |
| Ganita Manjari (Hindi) | hin | [acquisition-v4/books/ihmh1/ihmh101.pdf](../acquisition-v4/books/ihmh1/ihmh101.pdf) | 8 |
| Ganita Manjari (Hindi) | hin | [acquisition-v4/books/ihmh1/ihmh104.pdf](../acquisition-v4/books/ihmh1/ihmh104.pdf) | 12 |
| Ganita Manjari (Hindi) | hin | [acquisition-v4/books/ihmh1/ihmh108.pdf](../acquisition-v4/books/ihmh1/ihmh108.pdf) | 14 |
| Ganit | hin | [acquisition-v4/books/jhmh1/jhmh101.pdf](../acquisition-v4/books/jhmh1/jhmh101.pdf) | 6 |
| Ganit | hin | [acquisition-v4/books/jhmh1/jhmh107.pdf](../acquisition-v4/books/jhmh1/jhmh107.pdf) | 8 |
| Ganit | hin | [acquisition-v4/books/jhmh1/jhmh114.pdf](../acquisition-v4/books/jhmh1/jhmh114.pdf) | 9 |

## What the remaining PDFs mean

Of 175 local source PDFs, 18 supplied development passages and 16 are linked to the locked test partition; neither entered fitting. The other 73 are collected companion chapters/editions, inbox books or reference documents without PDF passage use in this run.

A downloaded PDF of a book whose publisher HTML was used is still not counted as a PDF fitting source. Original inbox PDFs are not automatically training data. No locked-test passage text was opened for this inventory.

The saved labels are provisional assistant labels. These counts do not establish model accuracy or redistribution rights. Source PDFs remain on the collection laptop. The repository retains the prepared passages, source receipts, partition assignments, trained classifier and this inventory.
