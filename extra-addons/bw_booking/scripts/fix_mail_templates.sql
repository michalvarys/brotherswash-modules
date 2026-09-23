-- ============================================================
-- Brothers Wash Detailing — Fix mail templates (3 languages)
-- Languages: cs_CZ, en_US, uk_UA
-- Fixes: Jinja2 variables, diacritics, price prefix,
--        company data from DB, multi-language support
-- ============================================================

-- Step 1: Allow module upgrade to overwrite templates
UPDATE ir_model_data
   SET noupdate = false
 WHERE module = 'bw_booking'
   AND name IN ('mail_template_booking_pending', 'mail_template_booking_confirmed');

-- Step 2: Update PENDING booking email template (3 languages)
UPDATE mail_template
   SET body_html = jsonb_build_object(
       'en_US', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#1a1a1a;margin-top:0;">Thank you for your reservation!</h2>
            <p>Hello, <strong>{{ object.customer_name }}</strong>,</p>
            <p>Your reservation has been successfully received and is awaiting confirmation. We will contact you to confirm the appointment.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Reservation number</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Vehicle</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or ''not specified'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Preferred date</td><td style="padding:10px;border:1px solid #ddd;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''not specified'' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Total price</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''from '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Selected services:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            % if object.customer_note:
            <p><strong>Your note:</strong> {{ object.customer_note }}</p>
            % endif
            <p style="margin-top:20px;color:#666;">Reservation status: <strong style="color:#e67e22;">Awaiting confirmation</strong></p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>',
       'cs_CZ', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#1a1a1a;margin-top:0;">Děkujeme za Vaši rezervaci!</h2>
            <p>Dobrý den, <strong>{{ object.customer_name }}</strong>,</p>
            <p>Vaše rezervace byla úspěšně přijata a čeká na potvrzení. Budeme Vás kontaktovat s potvrzením termínu.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Číslo rezervace</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Vozidlo</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or ''neuvedeno'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Preferovaný termín</td><td style="padding:10px;border:1px solid #ddd;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''neuvedeno'' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Celková cena</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''od '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Vybrané služby:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            % if object.customer_note:
            <p><strong>Vaše poznámka:</strong> {{ object.customer_note }}</p>
            % endif
            <p style="margin-top:20px;color:#666;">Stav Vaší rezervace: <strong style="color:#e67e22;">Čeká na potvrzení</strong></p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>',
       'uk_UA', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#1a1a1a;margin-top:0;">Дякуємо за Ваше бронювання!</h2>
            <p>Доброго дня, <strong>{{ object.customer_name }}</strong>,</p>
            <p>Ваше бронювання було успішно прийнято і очікує підтвердження. Ми зв''яжемося з Вами для підтвердження дати.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Номер бронювання</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Транспортний засіб</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or ''не вказано'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Бажана дата</td><td style="padding:10px;border:1px solid #ddd;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''не вказано'' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Загальна ціна</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''від '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Обрані послуги:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            % if object.customer_note:
            <p><strong>Ваша примітка:</strong> {{ object.customer_note }}</p>
            % endif
            <p style="margin-top:20px;color:#666;">Статус бронювання: <strong style="color:#e67e22;">Очікує підтвердження</strong></p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>'
       ),
       subject = jsonb_build_object(
           'en_US', '{{ object.env.company.name }} - Your reservation #{{ object.id }}',
           'cs_CZ', '{{ object.env.company.name }} - Vaše rezervace č. {{ object.id }}',
           'uk_UA', '{{ object.env.company.name }} - Ваше бронювання №{{ object.id }}'
       ),
       name = jsonb_build_object(
           'en_US', 'BWD: Reservation - Pending confirmation',
           'cs_CZ', 'BWD: Rezervace - Čeká na potvrzení',
           'uk_UA', 'BWD: Бронювання - Очікує підтвердження'
       )
 WHERE id = (SELECT res_id FROM ir_model_data WHERE module = 'bw_booking' AND name = 'mail_template_booking_pending');

-- Step 3: Update CONFIRMED booking email template (3 languages)
UPDATE mail_template
   SET body_html = jsonb_build_object(
       'en_US', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#27ae60;margin-top:0;">Your reservation has been confirmed!</h2>
            <p>Hello, <strong>{{ object.customer_name }}</strong>,</p>
            <p>We are pleased to confirm your reservation. We look forward to seeing you at the scheduled time.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Reservation number</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Date</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#27ae60;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''not specified'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Vehicle</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or '''' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Total price</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''from '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Selected services:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            <div style="margin:25px 0;padding:15px;background:#f0f9f0;border-left:4px solid #27ae60;">
                <p style="margin:0;"><strong>Address:</strong> {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p>
                <p style="margin:5px 0 0;">The event has been added to your calendar.</p>
            </div>
            <p style="color:#666;">If you need to change the date, please contact us.</p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>',
       'cs_CZ', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#27ae60;margin-top:0;">Vaše rezervace byla potvrzena!</h2>
            <p>Dobrý den, <strong>{{ object.customer_name }}</strong>,</p>
            <p>S radostí Vám potvrzujeme Vaši rezervaci. Očekáváme Vás v níže uvedeném termínu.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Číslo rezervace</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Termín</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#27ae60;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''neuvedeno'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Vozidlo</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or '''' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Celková cena</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''od '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Vybrané služby:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            <div style="margin:25px 0;padding:15px;background:#f0f9f0;border-left:4px solid #27ae60;">
                <p style="margin:0;"><strong>Adresa:</strong> {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p>
                <p style="margin:5px 0 0;">Událost byla přidána do Vašeho kalendáře.</p>
            </div>
            <p style="color:#666;">V případě potřeby změny termínu nás prosím kontaktujte.</p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>',
       'uk_UA', '<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" style="max-width:600px;margin:0 auto;background:#ffffff;">
        <tr><td style="background:#1a1a1a;padding:30px;text-align:center;"><h1 style="color:#c8a961;margin:0;font-size:24px;">{{ object.env.company.name }}</h1></td></tr>
        <tr><td style="padding:30px;">
            <h2 style="color:#27ae60;margin-top:0;">Ваше бронювання підтверджено!</h2>
            <p>Доброго дня, <strong>{{ object.customer_name }}</strong>,</p>
            <p>З радістю підтверджуємо Ваше бронювання. Чекаємо на Вас у зазначений час.</p>
            <table width="100%" style="margin:20px 0;border-collapse:collapse;">
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Номер бронювання</td><td style="padding:10px;border:1px solid #ddd;">BWD-{{ object.id }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Дата</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#27ae60;">{{ object.preferred_date and object.preferred_date.strftime(''%d.%m.%Y %H:%M'') or ''не вказано'' }}</td></tr>
                <tr style="background:#f5f5f5;"><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Транспортний засіб</td><td style="padding:10px;border:1px solid #ddd;">{{ object.vehicle_type_id.name }} - {{ object.vehicle_info or '''' }}</td></tr>
                <tr><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">Загальна ціна</td><td style="padding:10px;border:1px solid #ddd;font-weight:bold;color:#c8a961;">{{ object.is_price_approximate and ''від '' or '''' }}{{ ''%.0f'' % object.total_price }},- Kč</td></tr>
            </table>
            <h3 style="color:#1a1a1a;">Обрані послуги:</h3>
            <ul style="padding-left:20px;">% for line in object.line_ids:
                <li>{{ line.service_id.name }} - {{ line.price_prefix and line.price_prefix + '' '' or '''' }}{{ ''%.0f'' % line.price }},- Kč</li>
            % endfor</ul>
            <div style="margin:25px 0;padding:15px;background:#f0f9f0;border-left:4px solid #27ae60;">
                <p style="margin:0;"><strong>Адреса:</strong> {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p>
                <p style="margin:5px 0 0;">Подію додано до Вашого календаря.</p>
            </div>
            <p style="color:#666;">Якщо потрібно змінити дату, будь ласка, зв''яжіться з нами.</p>
        </td></tr>
        <tr><td style="background:#1a1a1a;padding:20px;text-align:center;color:#888;font-size:12px;"><p style="margin:0;">{{ object.env.company.name }} | {{ object.env.company.street or '''' }}, {{ object.env.company.city or '''' }}</p></td></tr>
    </table>
</div>'
       ),
       subject = jsonb_build_object(
           'en_US', 'Reservation confirmed - {{ object.env.company.name }} #{{ object.id }}',
           'cs_CZ', 'Potvrzení rezervace - {{ object.env.company.name }} č. {{ object.id }}',
           'uk_UA', 'Підтвердження бронювання - {{ object.env.company.name }} №{{ object.id }}'
       ),
       name = jsonb_build_object(
           'en_US', 'BWD: Reservation - Confirmed',
           'cs_CZ', 'BWD: Rezervace - Potvrzena',
           'uk_UA', 'BWD: Бронювання - Підтверджено'
       )
 WHERE id = (SELECT res_id FROM ir_model_data WHERE module = 'bw_booking' AND name = 'mail_template_booking_confirmed');

-- Verify:
SELECT name, substring(body_html::text, 1, 120) AS body_preview
  FROM mail_template
 WHERE id IN (
    SELECT res_id FROM ir_model_data
     WHERE module = 'bw_booking'
       AND name IN ('mail_template_booking_pending', 'mail_template_booking_confirmed')
 );
