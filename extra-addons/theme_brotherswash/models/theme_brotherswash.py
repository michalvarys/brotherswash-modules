from odoo import api, models

from .view_terms import VIEW_TERMS

# Menu labels: theme.website.menu (xmlid) -> (cs_CZ, en_US, uk_UA).
# The menus were created with Czech as the en_US source, so /en showed Czech labels.
MENU_TRANSLATIONS = {
    'menu_home': ('Domovská stránka', 'Homepage', 'Головна'),
    'menu_cenik': ('Ceník', 'Price List', 'Ціни'),
    'menu_sluzby': ('Služby', 'Services', 'Послуги'),
    'menu_galerie': ('Galerie', 'Gallery', 'Галерея'),
    'menu_rezervace': ('Rezervace', 'Reservation', 'Бронювання'),
    'menu_kontakt': ('Kontakt', 'Contact', 'Контакти'),
}


class ThemeBrothersWash(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_brotherswash_post_copy(self, mod):
        self.env['theme.brotherswash.translations']._bwd_fix_menu_translations()


class ThemeBrothersWashTranslations(models.AbstractModel):
    _name = 'theme.brotherswash.translations'
    _description = 'Brothers Wash theme translations fix'

    @api.model
    def _bwd_set_translations(self, record, fname, cs, en, uk):
        """Set cs/en/uk unless somebody already changed the text by hand."""
        installed = dict(self.env['res.lang'].get_installed())
        untouched = (cs, en, False, '')
        if record.with_context(lang='en_US')[fname] not in untouched:
            return
        translations = {'en_US': en}
        for lang, value in (('cs_CZ', cs), ('uk_UA', uk)):
            if lang in installed and record.with_context(lang=lang)[fname] in untouched:
                translations[lang] = value
        record.update_field_translations(fname, translations)

    @api.model
    def _bwd_fix_menu_translations(self):
        for xmlid, (cs, en, uk) in MENU_TRANSLATIONS.items():
            theme_menu = self.env.ref(f'theme_brotherswash.{xmlid}', raise_if_not_found=False)
            if not theme_menu:
                continue
            self._bwd_set_translations(theme_menu, 'name', cs, en, uk)
            for menu in self.env['website.menu'].with_context(active_test=False).search([('theme_template_id', '=', theme_menu.id)]):
                self._bwd_set_translations(menu, 'name', cs, en, uk)

    @api.model
    def _bwd_fix_edited_views(self):
        """Website copies of the snippets saved from the editor (arch_updated) are skipped
        by the theme upgrade and keep the old Czech source. Switch their Czech terms to the
        English source and store cs/uk as term translations; anything else is left alone."""
        installed = dict(self.env['res.lang'].get_installed())
        field = self.env['ir.ui.view']._fields['arch_db']
        views = self.env['ir.ui.view'].with_context(active_test=False).search([
            ('key', '=like', 'theme_brotherswash.%'), ('website_id', '!=', False),
        ])
        for view in views:
            source = view.with_context(lang='en_US').arch_db
            if not source:
                continue
            terms = [term for term in field.get_trans_terms(source) if term in VIEW_TERMS]
            if not terms:
                continue
            english = field.translate(lambda term: VIEW_TERMS[term][0] if term in VIEW_TERMS else term, source)
            view.with_context(lang='en_US').write({'arch_db': english})
            translations = {}
            if 'cs_CZ' in installed:
                translations['cs_CZ'] = {VIEW_TERMS[term][0]: term for term in terms}
            if 'uk_UA' in installed:
                translations['uk_UA'] = {VIEW_TERMS[term][0]: VIEW_TERMS[term][1] for term in terms}
            if translations:
                view.update_field_translations('arch_db', translations)
