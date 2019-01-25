#!/usr/bin/python3

from lxml import etree
from lxml.etree import fromstring
import os
import re


class AnnotationExtractor:
    def __init__(self, elan_file_name, wordforms):
        self.elan_file_name = elan_file_name
        self.elan_parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        self.elan_tree = fromstring(
            open(self.elan_file_name, encoding='utf-8').read().encode('utf-8'),
            parser=self.elan_parser
        )
        self.wordforms = wordforms
        self.mansi_tier = self.elan_tree.xpath('//TIER[@TIER_ID="Mansi"]')[0]
        self.mansi_annots = self.mansi_tier.xpath('ANNOTATION')
        self.russian_tier = self.elan_tree.xpath('//TIER[@TIER_ID="Russian"]')[0]
        self.russian_annots = self.russian_tier.xpath('ANNOTATION')
        self.morphemes_tier = self.elan_tree.xpath('//TIER[@TIER_ID="Morphemes"]')[0]
        self.morphemes_annots = self.morphemes_tier.xpath('ANNOTATION')
        self.glosses_tier = self.elan_tree.xpath('//TIER[@TIER_ID="Glosses"]')[0]
        self.glosses_annots = self.glosses_tier.xpath('ANNOTATION')

    def extend_wordforms_dict(self):
        for n in range(len(self.mansi_tier)):
            self.run_through_sentence(self.mansi_tier[n], self.morphemes_tier[n], self.glosses_tier[n])
        self.morphemes_tier.getparent().remove(self.morphemes_tier)
        self.glosses_tier.getparent().remove(self.glosses_tier)

    def run_through_sentence(self, mansi_annot, morphemes_annot, glosses_annot):
        morph = morphemes_annot.xpath("ALIGNABLE_ANNOTATION/ANNOTATION_VALUE")[0].text
        gloss = glosses_annot.xpath("ALIGNABLE_ANNOTATION/ANNOTATION_VALUE")[0].text
        mansi = mansi_annot.xpath("ALIGNABLE_ANNOTATION/ANNOTATION_VALUE")[0].text
        morph, gloss, mansi = morph.split(), gloss.split(), mansi.split()
        if len(morph) != len(gloss):
            print(morph)
            print(gloss)
            raise ValueError(self.elan_file_name)
        for n, token in enumerate(morph):
            w = etree.Element("w")
            token_gloss = gloss[n]
            token_gloss = re.sub(r'\[(.+?)\]', '.\g<1>', token_gloss)
            try:
                wordform = mansi[n]
            except IndexError:
                print(morph)
                print(gloss)
                print(mansi)
                raise ValueError(self.elan_file_name)
            if wordform in self.wordforms:
                continue
            if "-" in token_gloss:
                token_gloss_parts = token_gloss.split("-")
                stem_index = -1
                for index, gloss_part in enumerate(token_gloss_parts):
                    if re.search(r'[А-ЯЁа-яё]', gloss_part):
                        stem_index = index
                ana_tag = etree.SubElement(w, "ana")
                local_gloss = []
                trans_ru = None
                for index, gloss_part in enumerate(token_gloss_parts):
                    if re.search(r'[А-ЯЁа-яё]', gloss_part):
                        if index == stem_index:
                            local_gloss.append("STEM")
                            trans_ru = gloss_part
                            print('trans_ru:', trans_ru)
                            print(self.elan_file_name)
                        else:
                            local_gloss.append("unknown")
                    else:
                        local_gloss.append(gloss_part)
                ana_tag.set("parts", token)
                ana_tag.set("gloss", "-".join(local_gloss))
                if trans_ru:
                    ana_tag.set("trans_ru", trans_ru)
                ana_tag.tail = wordform
                self.wordforms[wordform] = w
            elif re.search(r'[А-ЯЁа-яё]', token_gloss):
                ana_tag = etree.SubElement(w, "ana")
                token_gloss_pct = token_gloss.split(".")
                contains_abbr = False
                for index, part in enumerate(token_gloss_pct):
                    if re.search(r'[A-Za-z]', part):
                        contains_abbr = index
                        break
                if contains_abbr and len(token_gloss_pct) > 1:
                    ana_tag.set("parts", token)
                    ana_tag.set("gloss", ".".join(["STEM"] + token_gloss_pct[contains_abbr:]))
                    ana_tag.set("trans_ru", " ".join(token_gloss_pct[:contains_abbr]))
                else:
                    ana_tag.set("trans_ru", " ".join(token_gloss.split(".")))
                ana_tag.tail = wordform
                self.wordforms[wordform] = w
            else:
                ana_tag = etree.SubElement(w, "ana")
                ana_tag.set("parts", token)
                ana_tag.set("gloss", "STEM." + token_gloss)
                ana_tag.tail = wordform
                self.wordforms[wordform] = w


wordforms = dict()
eafs = [file_name for file_name in os.listdir(".") if file_name.endswith(".eaf")]
for eaf_file in eafs:
    this = AnnotationExtractor(eaf_file, wordforms)
    this.extend_wordforms_dict()
    wordforms = this.wordforms
    with open("clear_eaf/%s" % eaf_file, "w", encoding="utf-8") as clear_eaf:
        clear_eaf.write(
            etree.tostring(this.elan_tree, encoding='utf-8', pretty_print=True).decode('utf-8')
        )
        clear_eaf.close()

with open("generated_parsings.txt", "a", encoding="utf-8") as pwl:
    for w_tag in wordforms.values():
        pwl.write(
            "\n" + etree.tostring(w_tag, encoding='utf-8').decode('utf-8')
        )
    pwl.close()
