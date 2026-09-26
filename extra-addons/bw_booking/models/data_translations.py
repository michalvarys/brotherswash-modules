from odoo import api, models

# The service data (data/bw_service_data.xml, noupdate) was written with Czech as the
# source (en_US) value, so /en showed Czech names and several /uk texts too.
# (xmlid, field): (cs_CZ, en_US, uk_UA)
DATA_TRANSLATIONS = {
    ('cat_premium', 'name'): ('Prémiové služby', 'Premium services', 'Преміум послуги'),
    ('cat_premium', 'description'): ('Dlouhodobá ochrana a profesionální péče', 'Long-lasting protection and professional care', 'Довготривалий захист і професійний догляд'),
    ('cat_program', 'name'): ('Ceník služeb', 'Service price list', 'Прайс-лист послуг'),
    ('cat_program', 'description'): ('Vyberte si program, který vám vyhovuje', 'Choose the programme that suits you', 'Оберіть програму, яка вам підходить'),
    ('cat_extra', 'name'): ('Doplňkové služby', 'Additional services', 'Додаткові послуги'),
    ('cat_extra', 'description'): ('Individuální péče podle vašich potřeb', 'Individual care tailored to your needs', 'Індивідуальний догляд відповідно до ваших потреб'),
    ('svc_keramika', 'name'): ('Keramická ochrana laku', 'Ceramic paint protection', 'Керамічний захист лаку'),
    ('svc_keramika', 'short_description'): ('Garantovaná ochrana až 3 roky', 'Guaranteed protection for up to 3 years', 'Гарантований захист до 3 років'),
    ('svc_lesteni', 'name'): ('Hloubkové leštění karoserie', 'Deep body polishing', 'Глибоке полірування кузова'),
    ('svc_lesteni', 'short_description'): ('Vícekroková korekce laku', 'Multi-step paint correction', 'Багатоетапна корекція лаку'),
    ('svc_fusso', 'short_description'): ('Dlouhodobý tuhý vosk', 'Long-lasting hard wax', 'Довготривалий твердий віск'),
    ('svc_program1', 'name'): ('Program 1', 'Programme 1', 'Програма 1'),
    ('svc_program2', 'name'): ('Program 2', 'Programme 2', 'Програма 2'),
    ('svc_program3', 'name'): ('Program 3', 'Programme 3', 'Програма 3'),
    ('svc_program4', 'name'): ('Program 4', 'Programme 4', 'Програма 4'),
    ('svc_program1', 'short_description'): ('Ruční mytí vozu', 'Hand car wash', 'Ручне миття авто'),
    ('svc_program2', 'short_description'): ('Ruční mytí + interiér', 'Hand wash + interior', 'Ручне миття + салон'),
    ('svc_program3', 'short_description'): ('Kompletní detailing', 'Complete detailing', 'Комплексний детейлінг'),
    ('svc_program4', 'short_description'): ('Interiér', 'Interior', 'Салон'),
    ('svc_program3', 'duration_info'): ('cca 6 hodin', 'approx. 6 hours', 'близько 6 годин'),
    ('svc_program1', 'duration_info'): ('15-25 min', '15-25 min', '15-25 хв'),
    ('svc_program2', 'duration_info'): ('60-90 min', '60-90 min', '60-90 хв'),
    ('svc_program4', 'duration_info'): ('60 min', '60 min', '60 хв'),
    ('svc_extra_koberecky', 'name'): ('Čištění textilních koberečků (tepování) + provonění', 'Textile floor mat shampooing + freshening', 'Хімчистка текстильних килимків + ароматизація'),
    ('svc_extra_okna', 'name'): ('Čištění a vyleštění vnějších oken a zrcátek', 'Cleaning and polishing of exterior windows and mirrors', 'Очищення та полірування зовнішніх вікон і дзеркал'),
    ('svc_extra_vysati', 'name'): ('Kompletní vysátí interiéru', 'Complete interior vacuuming', 'Повне пилосмоктання салону'),
    ('svc_extra_klima', 'name'): ('Čištění klimatizace', 'Air conditioning cleaning', 'Очищення кондиціонера'),
    ('svc_extra_strop', 'name'): ('Tepování stropu', 'Headliner shampooing', 'Хімчистка стелі'),
    ('svc_extra_gumove', 'name'): ('Mytí gumových koberečků', 'Rubber floor mat washing', 'Миття гумових килимків'),
    ('svc_extra_kuze', 'name'): ('Čištění a impregnace kůže', 'Leather cleaning and conditioning', 'Очищення та просочення шкіри'),
    ('svc_extra_sterace', 'name'): ('Tekuté stěrače, trvanlivost až 1 rok', 'Liquid wipers (rain repellent), lasts up to 1 year', 'Рідкі двірники (антидощ), до 1 року'),
    ('svc_extra_motor', 'name'): ('Mytí motoru (na vlastní riziko)', 'Engine wash (at your own risk)', 'Миття двигуна (на власний ризик)'),
    ('svc_extra_sedacky', 'name'): ('Hloubkové čištění (tepování) sedaček', 'Deep seat shampooing', 'Глибока хімчистка сидінь'),
    ('svc_extra_pneumatiky', 'name'): ('Ošetření pneumatik', 'Tyre dressing', 'Догляд за шинами'),
    ('svc_extra_voskovani', 'name'): ('Voskování vozu voskem s UV filtrem a teflonem', 'Waxing with UV filter and Teflon wax', 'Воскування авто воском з UV-фільтром і тефлоном'),
    ('svc_extra_vnitrni_plasty', 'name'): ('Očištění a ošetření vnitřních plastových dílů', 'Cleaning and treatment of interior plastics', 'Очищення та догляд за внутрішнім пластиком'),
    ('svc_extra_chlupy', 'name'): ('Čištění interiéru od chlupů', 'Pet hair removal from interior', 'Очищення салону від шерсті'),
    ('svc_extra_lesteni_dil', 'name'): ('Leštění jednotlivého dílu', 'Single panel polishing', 'Полірування окремої деталі'),
    ('svc_extra_podlaha', 'name'): ('Tepování podlahy', 'Floor carpet shampooing', 'Хімчистка підлоги'),
    ('svc_extra_venkovni_plasty', 'name'): ('Ošetření a konzervace venkovních plastových dílů', 'Treatment and protection of exterior plastics', 'Догляд та консервація зовнішнього пластику'),
    ('svc_extra_alu', 'name'): ('Mytí a vyčištění ALU disků', 'Alloy wheel cleaning', 'Миття та очищення литих дисків'),
    ('svc_extra_asfalt', 'name'): ('Odstranění asfaltu', 'Tar removal', 'Видалення бітуму'),
    ('svc_extra_polepy', 'name'): ('Odstranění polepů', 'Sticker and wrap removal', 'Видалення наклейок'),
    ('vehicle_type_sedan', 'name'): ('Sedan', 'Sedan', 'Седан'),
    ('vehicle_type_suv', 'name'): ('SUV', 'SUV', 'Позашляховик (SUV)'),
}
PRICE_PREFIX = ('od', 'from', 'від')

# Service descriptions are translated term by term (sentences / list items).
# cs_CZ term -> (en_US term, uk_UA term)
DESCRIPTION_SERVICES = ['svc_keramika', 'svc_lesteni', 'svc_fusso', 'svc_program1', 'svc_program2', 'svc_program3', 'svc_program4']
DESCRIPTION_TERMS = {
    'Profesionální keramický povlak vytvářející tvrdou ochrannou vrstvu. Chrání lak před UV zářením, solí, chemikáliemi, hmyzem i drobnými škrábanci.': (
        'Professional ceramic coating creating a hard protective layer. Protects paint against UV rays, salt, chemicals, insects and minor scratches.',
        'Професійне керамічне покриття, що створює твердий захисний шар. Захищає лак від ультрафіолету, солі, хімікатів, комах та дрібних подряпин.'),
    'Součást balíčku je servisní kniha a kontrola každých 6 měsíců:': (
        'Package includes a service book and inspection every 6 months:',
        'До пакету входить сервісна книга та перевірка кожні 6 місяців:'),
    'Kontrola stavu keramické ochrany': ('Ceramic protection condition check', 'Перевірка стану керамічного захисту'),
    'Údržbové mytí vozu zdarma': ('Free maintenance wash', 'Сервісне миття автомобіля безкоштовно'),
    'Případné doplnění ochranné vrstvy': ('Optional protective layer top-up', 'За потреби доповнення захисного шару'),
    'Profesionální strojní leštění odstraňující jemné i střední škrábance, hologramy, oxidaci a stopy po špatném mytí.': (
        'Professional machine polishing removing fine and medium scratches, holograms, oxidation and marks from improper washing.',
        'Професійне машинне полірування, що усуває дрібні та середні подряпини, голограми, окислення та сліди від неправильного миття.'),
    'Chemická a mechanická dekontaminace laku': ('Chemical and mechanical paint decontamination', 'Хімічна та механічна деконтамінація лаку'),
    'Vícekrokové strojní leštění profesionálními pastami': ('Multi-step machine polishing with professional compounds', 'Багатоетапне машинне полірування професійними пастами'),
    'Závěrečná kontrola kvality': ('Final quality inspection', 'Фінальна перевірка якості'),
    'Japonský syntetický vosk s výdrží až 12 měsíců. Poskytuje silnou ochranu proti vodě, soli, UV záření a silniční chemii.': (
        'Japanese synthetic wax lasting up to 12 months. Provides strong protection against water, salt, UV rays and road chemicals.',
        'Японський синтетичний віск з терміном дії до 12 місяців. Забезпечує надійний захист від води, солі, ультрафіолету та дорожньої хімії.'),
    '<strong>+ Dekontaminace laku</strong> (odstranění asfaltu, polétavé rzi apod.)': (
        '<strong>+ Paint decontamination</strong> (removal of tar, iron fallout, etc.)',
        '<strong>+ Деконтамінація лаку</strong> (видалення асфальту, летючої іржі тощо)'),
    'Ruční mytí vozu': ('Hand car wash', 'Ручне миття автомобіля'),
    'Speciální odstranění zaschlého hmyzu': ('Special dried insect removal', 'Спеціальне видалення засохлих комах'),
    'Mytí vnitřních hran dveří, prahů a podblatníků': ('Cleaning door jambs, sills and wheel arches', 'Миття внутрішніх кромок дверей, порогів та підкрилків'),
    'Mytí gumových koberečků': ('Rubber mat cleaning', 'Миття гумових килимків'),
    'Mytí disků kol': ('Wheel cleaning', 'Миття колісних дисків'),
    'Kompletní vysušení karoserie': ('Complete body drying', 'Повне висушування кузова'),
    'Vyleštění vnějších oken a zrcátek': ('Polishing exterior windows and mirrors', 'Полірування зовнішніх вікон та дзеркал'),
    'Ošetření pneumatik': ('Tire dressing', 'Обробка шин'),
    'Vyleštění vnitřních i vnějších oken a zrcátek': ('Polishing interior and exterior windows and mirrors', 'Полірування внутрішніх та зовнішніх вікон і дзеркал'),
    'Kompletní vyluxování interiéru': ('Complete interior vacuuming', 'Повне пилососіння салону'),
    'Kompletní vysátí interiéru': ('Complete interior vacuuming', 'Повне пилососіння салону'),
    'Očištění a ošetření plastových vnitřních i vnějších dílů': ('Cleaning and treating interior and exterior plastic trim', 'Очищення та обробка пластикових внутрішніх і зовнішніх деталей'),
    'Provonění interiéru': ('Interior fragrance', 'Ароматизація салону'),
    'Vyleštění vnitřních i vnějších oken': ('Polishing interior and exterior windows', 'Полірування внутрішніх та зовнішніх вікон'),
    'Vyleštění zrcátek': ('Mirror polishing', 'Полірування дзеркал'),
    'Kompletní tepování textilního interiéru (mokrou cestou)': ('Complete textile interior extraction cleaning (wet method)', 'Повна хімчистка текстильного салону (мокрим способом)'),
    'Ošetření a konzervace vnitřních plastů': ('Interior plastic treatment and protection', 'Обробка та консервація внутрішніх пластиків'),
    'Mytí oken': ('Window cleaning', 'Миття вікон'),
}


class BwDataTranslations(models.AbstractModel):
    _name = 'bw.data.translations'
    _description = 'Brothers Wash data translations fix'

    @api.model
    def _bw_apply(self, record, fname, cs, en, uk):
        """Set cs/en/uk unless somebody already changed the text by hand."""
        installed = dict(self.env['res.lang'].get_installed())
        untouched = (cs, en, False, '')
        if record.with_context(lang='en_US')[fname] not in untouched:
            return
        translations = {'en_US': en}
        for lang, value in (('cs_CZ', cs), ('uk_UA', uk)):
            # uk may already hold a proper translation from the PO file: keep it
            if lang in installed and record.with_context(lang=lang)[fname] in untouched:
                translations[lang] = value
        record.update_field_translations(fname, translations)

    @api.model
    def _bw_fix_data_translations(self):
        for (xmlid, fname), (cs, en, uk) in DATA_TRANSLATIONS.items():
            record = self.env.ref(f'bw_booking.{xmlid}', raise_if_not_found=False)
            if record:
                self._bw_apply(record, fname, cs, en, uk)
        for price in self.env['bw.service.price'].search([]):
            if price.with_context(lang='en_US').price_prefix == PRICE_PREFIX[0]:
                self._bw_apply(price, 'price_prefix', *PRICE_PREFIX)
        self._bw_fix_descriptions()

    @api.model
    def _bw_fix_descriptions(self):
        installed = dict(self.env['res.lang'].get_installed())
        cs_terms = sorted(DESCRIPTION_TERMS, key=len, reverse=True)
        for xmlid in DESCRIPTION_SERVICES:
            service = self.env.ref(f'bw_booking.{xmlid}', raise_if_not_found=False)
            if not service:
                continue
            # str(): Markup.replace() would escape the <strong> of the terms
            source = str(service.with_context(lang='en_US').description or '')
            present = [cs for cs in cs_terms if cs in source]
            if not present:
                continue  # already English (or edited by hand)
            english = source
            for cs in present:
                english = english.replace(cs, DESCRIPTION_TERMS[cs][0])
            service.with_context(lang='en_US').write({'description': english})
            translations = {}
            if 'cs_CZ' in installed:
                translations['cs_CZ'] = {DESCRIPTION_TERMS[cs][0]: cs for cs in present}
            if 'uk_UA' in installed:
                translations['uk_UA'] = {DESCRIPTION_TERMS[cs][0]: DESCRIPTION_TERMS[cs][1] for cs in present}
            if translations:
                service.update_field_translations('description', translations)
