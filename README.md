# MusakBrainz

A CLI tool to more easily submit data to MusicBrainz

Tired of signing into the website and comparing data manually? Run this against a local music download:

```
python musakbrainz.py ~/path/to/some/album
```


If there are local files not represented in MB you'll be prompted to open the correct web page to add information. Otherwise, it'll show you that it found the data remotely:

```
$ python musakbrainz.py ~/Downloads/A\ Plus\ D/Best\ of\ Bootie\ Mashup\ 2023

Found 3 potential releases with the same track-count difference=0:
1) Adriana A - Best of Bootie Mashup 2023 [MBID=4d883ba2-b113-408b-942b-532e4478e4ec]  (Tracks=21)
2) Adriana A - Best of Bootie Mashup 2023 [MBID=4d0a4df5-2ade-44e5-b31c-fc448536cfd2]  (Tracks=21)
3) Adriana A - Best Bootie Mashup 2021 [MBID=2351b925-fed0-49d6-9353-83852f1d2383]  (Tracks=21)
Enter a number 1..3, or press Enter to cancel: 2
========================================================================================================================
RELEASE-LEVEL COMPARISON
========================================================================================================================
Artist: Unknown Local Artist                                 | Artist: Adriana A
  == Album:  Best of Bootie Mashup 2023
(subdir logic not shown at release-level)                    | MB Release URI: https://musicbrainz.org/release/4d0a4df5-2ade-44e5-b31c-fc448536cfd2
                                                             |  - download for free: https://bootiemashup.com/best-of-bootie/2023/

========================================================================================================================
TRACK-BY-TRACK COMPARISON
========================================================================================================================
File:    01 Adriana A & DJ Tyme - Bootie Mashup Intro 2023.mp3 | URI:     https://musicbrainz.org/recording/e2da9cbd-4f80-485b-b027-e58d9353cfb5
  == Track#:  1
  == Title:   Bootie Mashup Intro 2023
  == Artist:  Adriana A & DJ Tyme
------------------------------------------------------------------------------------------------------------------------
File:    02 HallMighty - Dance, Dance The Night.mp3          | URI:     https://musicbrainz.org/recording/eeb504e1-fefa-48d5-864f-29aa20317d2f
  == Track#:  2
  == Title:   Dance, Dance The Night (Fall Out Boy vs. Dua Lipa)
  == Artist:  HallMighty
------------------------------------------------------------------------------------------------------------------------
File:    03 Kill_mR_DJ - Funky Makeba.mp3                    | URI:     https://musicbrainz.org/recording/10150b5e-d6f2-436f-9f52-db8391ed03de
  == Track#:  3
  == Title:   Funky Makeba (Jain vs. Daft Punk vs. Crystal Waters)
  == Artist:  Kill_mR_DJ
------------------------------------------------------------------------------------------------------------------------
File:    04 iWillBattle - new rules, right?.mp3              | URI:     https://musicbrainz.org/recording/e0203570-df7d-4ddc-b6e6-60c842281452
  == Track#:  4
Title:   new rules, right? (Olivia Rodrigo vs. Dua Lipa)     | Title:   New rules, right? (Olivia Rodrigo vs. Dua Lipa)
  == Artist:  iWillBattle
------------------------------------------------------------------------------------------------------------------------
File:    05 Marc Johnce - Don't You Want Bloody Mary.mp3     | URI:     https://musicbrainz.org/recording/16697cba-723c-474c-b6c7-3266a9430d8b
  == Track#:  5
Title:   Don't You Want Bloody Mary (Lady Gaga vs. Human League vs. Purple Disco Machine) | Title:   Don’t You Want Bloody Mary (Lady Gaga vs. Human League vs. Purple Disco Machine)
  == Artist:  Marc Johnce
------------------------------------------------------------------------------------------------------------------------
File:    06 Lobsterdust - Incredible Bongos.mp3              | URI:     https://musicbrainz.org/recording/30012f3b-206d-4ca0-a018-c7928a3720df
  == Track#:  6
  == Title:   Incredible Bongos (Cardi B ft. Megan Thee Stallion vs. The Incredible Bongo Band)
  == Artist:  Lobsterdust
------------------------------------------------------------------------------------------------------------------------
File:    07 Sir Glo - Better Off Creepin' Alone.mp3          | URI:     https://musicbrainz.org/recording/8c5a66ea-8cca-4267-a5b3-d243f1700325
  == Track#:  7
Title:   Better Off Creepin' Alone (The Weeknd vs. Alice Deejay vs. Pickle) | Title:   Better Off Creepin’ Alone (The Weeknd vs. Alice Deejay vs. Pickle)
  == Artist:  Sir Glo
------------------------------------------------------------------------------------------------------------------------
File:    08 Lachie Le Grand - Drop That Low Last Night.mp3   | URI:     https://musicbrainz.org/recording/5a1e1e67-ea54-4615-b7ff-fd536c843f09
  == Track#:  8
  == Title:   Drop That Low Last Night (Morgan Wallen vs. Tujamo)
  == Artist:  Lachie Le Grand
------------------------------------------------------------------------------------------------------------------------
File:    09 SPICE - Boy's A Sweaty Liar.mp3                  | URI:     https://musicbrainz.org/recording/ab34d7a1-f47a-4f9f-ae80-3538c4586899
  == Track#:  9
Title:   Boy's A Sweaty Liar (PinkPantheress & Ice Spice vs. ESSEL) | Title:   Boy’s A Sweaty Liar (PinkPantheress & Ice Spice vs. ESSEL)
  == Artist:  SPICE
------------------------------------------------------------------------------------------------------------------------
File:    10 Marc Johnce - High & Low Alone (Padam Padam).mp3 | URI:     https://musicbrainz.org/recording/a54ef389-8af1-42fe-83ef-dc1123a5b74a
  == Track#:  10
  == Title:   High & Low Alone (Padam Padam) (Kylie Minogue vs. Kim Petras ft. Nicki Minaj vs. FLEXX)
  == Artist:  Marc Johnce
------------------------------------------------------------------------------------------------------------------------
File:    11 Mo27Da - The Way I Paint The Town Red.mp3        | URI:     https://musicbrainz.org/recording/fe9236dc-2bc0-4a31-94f6-84cb187513f1
  == Track#:  11
  == Title:   The Way I Paint The Town Red (Doja Cat vs. Timbaland, Keri Hilson vs. D.O.E & Sebastian)
  == Artist:  Mo27Da
------------------------------------------------------------------------------------------------------------------------
File:    12 Mo27Da - Why Escapism Feel So Bad.mp3            | URI:     https://musicbrainz.org/recording/d4ca8b0e-2641-4234-9094-134eb6cbf44f
  == Track#:  12
  == Title:   Why Escapism Feel So Bad (Raye & 070 Shake vs. Moby vs. Ferry Corsten)
  == Artist:  Mo27Da
------------------------------------------------------------------------------------------------------------------------
File:    13 DJ Firth - Born Slippy Flowers.mp3               | URI:     https://musicbrainz.org/recording/5ce4658a-055e-4d7e-95ae-b1048065ae55
  == Track#:  13
Title:   Born Slippy Flowers (Miley Cyrus vs. Underworld) [Radio Edit] | Title:   Born Slippy Flowers (Miley Cyrus vs. Underworld)
  == Artist:  DJ Firth
------------------------------------------------------------------------------------------------------------------------
File:    14 oki - Guerilla Voulez Vous.mp3                   | URI:     https://musicbrainz.org/recording/4e8cf64b-5038-4068-93b8-08aa48910963
  == Track#:  14
  == Title:   Guerilla Voulez Vous (ABBA vs. Rage Against The Machine)
  == Artist:  oki
------------------------------------------------------------------------------------------------------------------------
File:    15 MixmstrStel - Houdini Barbie.mp3                 | URI:     https://musicbrainz.org/recording/c9d5ab92-4863-4d1f-9899-b6b87af30591
  == Track#:  15
  == Title:   Houdini Barbie (Dua Lipa vs. Aqua)
  == Artist:  MixmstrStel
------------------------------------------------------------------------------------------------------------------------
File:    16 Aggro1 - Anti-Hero God.mp3                       | URI:     https://musicbrainz.org/recording/5974dc5e-6bb6-4891-bb3e-243fb6e8862d
  == Track#:  16
  == Title:   Anti-Hero God (Taylor Swift vs. Ghost Data)
  == Artist:  Aggro1
------------------------------------------------------------------------------------------------------------------------
File:    17 DJ J-Brew - Cruel Summertime.mp3                 | URI:     https://musicbrainz.org/recording/9bb5d002-7ead-486b-9ffd-4a1d00ee14b3
  == Track#:  17
  == Title:   Cruel Summertime (Taylor Swift vs. Semisonic)
  == Artist:  DJ J-Brew
------------------------------------------------------------------------------------------------------------------------
File:    18 Titus Jones - Where Is My Vampire Blood.mp3      | URI:     https://musicbrainz.org/recording/0aaa1aa3-fae6-48dc-b6c6-d64fda3f7614
  == Track#:  18
  == Title:   Where Is My Vampire Blood (Olivia Rodrigo vs. Taylor Swift vs. Placebo covering Pixies)
  == Artist:  Titus Jones
------------------------------------------------------------------------------------------------------------------------
File:    19 Adriana A - I Keep Forgettin You Got A Fast Car.mp3 | URI:     https://musicbrainz.org/recording/d84e4384-cf3f-42b7-b21a-1c0e93ca2744
  == Track#:  19
Title:   I Keep Forgettin' You Got A Fast Car (Luke Combs vs. Michael McDonald) | Title:   I Keep Forgettin’ You Got A Fast Car (Luke Combs vs. Michael McDonald)
  == Artist:  Adriana A
------------------------------------------------------------------------------------------------------------------------
File:    20 Vixoria Drift - As It Was When Snow Went Down....mp3 | URI:     https://musicbrainz.org/recording/a76f5c9e-209e-49fd-91e9-47c993e24b39
  == Track#:  20
Title:   As It Was When Snow Went Down... (Harry Styles vs. The Cure vs. Halsey + more) | Title:   As It Was When Snow Went Down... (The Cure vs. Harry Styles vs. Halsey vs. Lil Nas X)
  == Artist:  Vixoria Drift
------------------------------------------------------------------------------------------------------------------------
File:    21 There I Ruined It - Johnny Cash Sings "Barbie Girl" & More.mp3 | URI:     https://musicbrainz.org/recording/d26af888-e7a5-4973-9cbc-1711e051df5b
  == Track#:  21
Title:   Johnny Cash Sings "Barbie Girl" & More (A.I. Cover) | Title:   Johnny Cash Sings “Barbie Girl” & More (A.I. Cover)
  == Artist:  There I Ruined It
------------------------------------------------------------------------------------------------------------------------

Release has Release-Group: 4633f9fb-cc31-4ce2-ae2a-29bb7dd91e68 (Best of Bootie Mashup 2023)

Done. Exiting.
```
