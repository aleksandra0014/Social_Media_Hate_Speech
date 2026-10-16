import re
from collections import namedtuple

Term = namedtuple('Term', 'name pattern category needs_context target')

_PL = str.maketrans('ąćęłńóśźż', 'acelnoszz')

UA, MIG = 'Ukraińcy', 'migranci'
_TERMS = [
    # obelgi etniczne wobec Ukraińców
    ('ukrop', r'\bukrop\w*', 'obelga_etniczna', False, UA),
    ('ukry', r'\bukr(?:y|ow|om|ami|ach)\b', 'obelga_etniczna', False, UA),
    ('ukro-*', r'\bukro(?!p|i|j)[a-z]{3,}\w*', 'obelga_etniczna_zlozenie', False, UA),
    ('chachol', r'\bchach(?:o)?l\w*', 'obelga_etniczna', False, UA),
    ('chochol', r'\bchoch(?:o)?l(?:y|ow|om|ami)\b', 'obelga_etniczna', True, UA),
    ('upainiec', r'\bupa-?(?:in|ow)\w*|\bupowc\w*|\bupowiec\w*', 'obelga_historyczna', False, UA),
    ('upadlina', r'\bupadlin\w*', 'obelga_historyczna', False, UA),
    ('banderowiec', r'\bbanderow\w*', 'kod_historyczny', False, UA),
    ('banderyzm', r'\b(?:neo)?banderyzm\w*|\bbanderland\w*|\bbanderstadt\w*', 'kod_historyczny', False, UA),
    ('banderlog', r'\bbanderlog\w*', 'kod_historyczny', False, UA),
    ('bandera', r'\bbander(?:a|y|ze|e|zy)\b', 'kod_historyczny', True, UA),
    ('upa', r'\bupa\b', 'kod_historyczny', True, UA),
    ('rezun', r'\brz?ezun\w*|\brizun\w*', 'obelga_historyczna', False, UA),
    ('siekiernik', r'\bsiekiern(?:ik|icy|ikow|ikom|ikami)\b', 'obelga_historyczna', False, UA),
    ('herojam_slawa', r'\b(?:h|g)erojam\w*(?:\s+sla[wv]a)?', 'kod_historyczny', True, UA),
    ('slava_ukraini', r'\bsla[wv]a\s+ukrai?n\w*', 'kod_ironiczny', True, UA),
    ('ss_galizien', r'\bss[\s-]*galizien\b|\bdywizj\w*\s+galizien\b|\bhalyczyn\w*', 'kod_historyczny', False, UA),
    ('czerwono_czarna', r'\bczerwono[\s-]*czarn\w*', 'kod_historyczny', True, UA),
    ('wolyn_kod', r'\bwolyn\w*\s+(?:pamietamy|sie\s+powtorzy|powtorka)|\bpamietamy\s+(?:o\s+)?wolyn\w*'
                  r'|\bnie\s+zapomnimy\s+wolyn\w*', 'kod_historyczny', True, UA),
    # kody spiskowe i inwazji
    ('ukrainizacja', r'\bukrainizacj\w*|\bukrainizuj\w*|\bzukrainizowan\w*|\bukrainopolin\w*|\bukropolin\w*',
     'kod_spiskowy', False, UA),
    ('stop_ukrainizacji', r'#?stopukrainizacj\w*|\bstop\s+ukrainizacj\w*', 'kod_spiskowy', False, UA),
    ('polin', r'\bpolin\b|\bpolinia\w*', 'kod_spiskowy', True, UA),
    ('wymiana_ludnosci', r'\bwymian\w*\s+ludnosc\w*|\bwielk\w*\s+wymian\w*|\bzastepowani\w*\s+polakow|\bkalerg\w*',
     'kod_spiskowy', False, MIG),
    ('zalew_ukraincow', r'\bzalew\w*\s+(?:\w+\s+){0,2}ukrai?n\w*|\bnajazd\w*\s+ukrai?n\w*|\binwazj\w*\s+ukrai?nc\w*',
     'kod_inwazji', False, UA),
    ('najezdzcy_inwazja', r'\bnajezdz\w*|\b(?:inwazj|najazd)\w*\s+(?:imigrant|migrant|islam|uchodz|nachodz)\w*',
     'kod_inwazji', True, MIG),
    ('okupant', r'\bokupan(?:t|ci|tow|tom|tami)\b', 'kod_inwazji', True, UA),
    ('remigracja', r'\bremigrac\w*', 'kod', True, MIG),
    ('multikulti', r'\bmultikult\w*', 'kod', True, MIG),
    ('ubogacacze', r'\bubogac\w*', 'kod_ironiczny', False, MIG),
    ('ahmedy_mahomety', r'\bahmed(?:y|ow|ami)\b|\bmahomet(?:y|ow|ami)\b', 'kod', True, 'muzułmanie'),
    # obelgi wobec migrantów, muzułmanów, osób czarnoskórych
    ('nachodzcy', r'\bnachodz(?:c|stw)\w*', 'obelga', False, 'uchodźcy'),
    ('nielegalsi', r'\bnielegals\w*', 'obelga', False, MIG),
    ('ciapaci', r'\bciapa(?:t|c|k)\w*', 'obelga', False, MIG),
    ('kozojebcy', r'\bkozojeb\w*', 'obelga', False, 'muzułmanie'),
    ('arabusy', r'\barabus\w*', 'obelga', False, 'Arabowie'),
    ('czarnuchy', r'\bczarnuch\w*', 'obelga', False, 'osoby czarnoskóre'),
    ('murzyni', r'\bmurzyn\w*', 'obelga', True, 'osoby czarnoskóre'),
    ('bambusy', r'\bbambus\w*|\bbambo\b', 'obelga', True, 'osoby czarnoskóre'),
    ('brudasy', r'\bbrudas\w*', 'obelga', True, MIG),
    # dehumanizacja i stereotypy
    ('szarancza', r'\bszaranc\w*', 'dehumanizacja', True, MIG),
    ('darmozjad', r'\bdarmozjad\w*', 'dehumanizacja', True, MIG),
    ('bydlo_holota', r'\bbydl(?:o|a|em|u)\b|\bholot\w*|\bdzicz[aey]?\b|\bpodludz\w*|\bscierw\w*', 'dehumanizacja', True, MIG),
    ('roszczeniowi', r'\broszczeniow\w*', 'stereotyp', True, UA),
    ('niewdzieczni', r'\bniewdzieczn\w*|\bgdzie\s+(?:jest\s+)?(?:ta\s+)?wdzieczn\w*', 'stereotyp', True, UA),
    ('socjal_turysci', r'\bsocjal\w*\s+turys\w*|\bturys\w*\s+socjal\w*', 'stereotyp_swiadczenia', False, MIG),
    ('ukrainska_mafia', r'\bukrainsk\w*\s+mafi\w*|\bmafi\w*\s+ukrainsk\w*', 'stereotyp', False, UA),
    ('natasza', r'\bnatasz\w*', 'stereotyp_seksistowski', True, UA),
    ('brat_ukrainiec_iron', r'\bbra(?:t|cia|ci)\s+ukrai?n\w*|\bbratni\w*\s+narod\w*', 'kod_ironiczny', True, UA),
    # kody prorosyjskiej propagandy
    ('junta_kijowska', r'\b(?:junt|chunt)\w*\s+kijowsk\w*|\bkijowsk\w*\s+(?:junt|chunt|rezim)\w*|\bdenazyfikacj\w*',
     'kod_prorosyjski', False, UA),
    ('ukr_nazisci', r'\b(?:neo)?nazis\w*\s+ukrai?n\w*|\bukrai?n\w*\s+(?:neo)?nazis\w*|\bukrai?n\w*\s+faszys\w*'
                    r'|\bfaszys\w*\s+ukrai?n\w*', 'kod_prorosyjski', False, UA),
    # wezwania do wydalenia
    ('wypad_na_ukraine', r'\b(?:wypierdala\w*|wypad\w*|won|precz|wynocha)\s+(?:\w+\s+){0,3}(?:na|do)\s+'
                         r'(?:ukrai?n\w*|siebie|domu)|\bukrai?nc\w*\s+(?:\w+\s+){0,2}(?:do\s+domu|won|precz|wynocha)',
     'wezwanie_do_wydalenia', False, UA),
    ('deportowac', r'\bdeportowac\s+(?:\w+\s+){0,2}ukrai?n\w*|\bodeslac\s+(?:\w+\s+){0,2}ukrai?n\w*',
     'wezwanie_do_wydalenia', False, UA),
]
TERMS = [Term(name, re.compile(p), cat, ctx, target) for name, p, cat, ctx, target in _TERMS]


def fold(text):
    return str(text).lower().translate(_PL)


def find_slurs(text):
    """Terms found in text, in list order."""
    t = fold(text)
    return [term for term in TERMS if term.pattern.search(t)]


def slur_columns(text):
    """(names, categories, needs_context) for a CSV row; needs_context = 1 when every match depends on context."""
    found = find_slurs(text)
    if not found:
        return '', '', ''
    return ('; '.join(t.name for t in found), '; '.join(dict.fromkeys(t.category for t in found)),
            '1' if all(t.needs_context for t in found) else '0')
