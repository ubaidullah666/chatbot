"""Reproduce the fictional, authored ApexDrive teaching corpus. Run only to reset it."""
from pathlib import Path
from app.domain_config import FLEET_CATALOG, INSURANCE_TIERS, OPTIONAL_ADDONS, RENTAL_POLICIES


def main():
    root = Path('data/documents')
    root.mkdir(parents=True, exist_ok=True)
    documents = {}
    for category, details in FLEET_CATALOG.items():
        documents[f'fleet-{category.lower()}'] = f'{category} fleet category', str(details)
        for model in details['models']:
            documents['model-' + model.lower().replace(' ', '-')] = model, f'{model} belongs to the {category} category. Base rate is ${details["daily_rate"]} per 24-hour rental day. Model requests are preferences; an equivalent category vehicle may be supplied. Availability must be confirmed by staff. Category specifications: {details}'
    for name, details in INSURANCE_TIERS.items():
        documents['insurance-' + name.lower().replace(' ', '-')] = name, str(details) + ' Coverage excludes deliberate damage, unauthorized drivers and prohibited use. Report incidents to staff promptly; a waiver does not authorize unsafe driving.'
    for name, details in OPTIONAL_ADDONS.items():
        documents['addon-' + name.lower().replace(' ', '-')] = name, str(details) + ' Request this add-on before pickup. Staff confirm availability. Charges apply for every rental day; unused days are not refunded after collection.'
    for i, policy in enumerate(RENTAL_POLICIES):
        documents[f'policy-{i+1:02}'] = policy.split(':')[0], policy
    extra = {
        'airport-hours': ('Airport collection hours', 'The Airport desk opens daily from 06:00 to 23:00. Collect at the ground-floor rental counter in arrivals. After-hours pickup is unavailable. Provide a flight number so staff can review delays.'),
        'downtown-hours': ('Downtown collection hours', 'Downtown City Center opens Monday to Saturday 08:00 to 18:00 and Sunday 09:00 to 13:00. Collection outside these hours is unavailable.'),
        'late-flight': ('Delayed flight arrival', 'If your flight is delayed, contact the Airport desk before closing. A flight number does not guarantee a held car or an after-hours pickup. Staff must confirm a revised collection time.'),
        'return-airport': ('Airport returns', 'Airport returns use the signed rental-return lane on level P1. Photograph the vehicle and fuel gauge. Key-drop returns are accepted overnight; responsibility ends only after the next staffed inspection.'),
        'return-downtown': ('Downtown returns', 'Return Downtown vehicles to bays 1 through 6 behind the office. No unattended key-drop is available. Arrange a staffed return during opening hours.'),
        'late-return': ('Late return charges', 'A 29-minute grace period applies. From minute 30 through minute 119, a $20 late fee applies. At 120 minutes late, an additional rental day is charged instead of the $20 fee. Notify staff before the due time.'),
        'extension': ('Extending a rental', 'Request an extension before the scheduled return. Staff must approve availability and payment authorization. Continuing to drive is not automatic approval; approved extensions use the contracted daily category rate.'),
        'early-return': ('Early return', 'Early returns are accepted during branch hours. Prepaid unused days are nonrefundable. Pay-at-counter rentals are recalculated using complete 24-hour days with a minimum one-day charge.'),
        'one-way': ('One-way rentals', 'Airport to Downtown or Downtown to Airport returns incur a $35 one-way fee when approved before pickup. Returns to any other location are unavailable.'),
        'cross-border': ('Cross-border travel', 'Vehicles must remain within the country of rental. International border crossings are prohibited even with additional insurance. Domestic travel is permitted on public paved roads.'),
        'off-road': ('Prohibited roads', 'Off-road driving, beaches, racing tracks and unpaved trails are prohibited for every category, including AWD SUVs. AWD does not change this restriction.'),
        'smoking': ('Smoking and vaping', 'Smoking and vaping are prohibited inside all vehicles. Verified smoke contamination incurs a $150 cleaning charge. Report pre-existing odors at pickup.'),
        'pets': ('Pets in rental vehicles', 'Pets may travel in carriers. Remove animal hair before return; excessive hair or staining incurs a $75 cleaning charge. Assistance animals do not require carriers; ordinary damage rules still apply.'),
        'cleaning': ('Cleaning charges', 'Normal road dust requires no paid cleaning. Excessive mud, food staining or rubbish incurs a $50 cleaning fee. Smoke and pet contamination follow their separate policies; staff document the condition.'),
        'lost-keys': ('Lost vehicle keys', 'Notify staff immediately if keys are lost. Replacement is charged at documented supplier cost plus a $25 administration fee. Roadside Plus covers lockout assistance but not key replacement.'),
        'traffic-fines': ('Traffic violations', 'The renter pays traffic and parking fines from the rental period. ApexDrive charges a $15 processing fee per notice. Dispute the fine with its issuing authority.'),
        'tolls': ('Toll roads', 'Tolls are billed at actual cost plus a $3 daily administration fee only on days with toll activity. Administration fees are capped at $21 per rental. Toll charges may arrive after return.'),
        'accident': ('Accident procedure', 'Stop safely, contact emergency services if needed, and notify ApexDrive staff as soon as safe. Exchange details and photograph damage. Do not admit liability or authorize repairs without staff approval.'),
        'breakdown': ('Mechanical breakdown', 'Park safely and contact the assistance number printed on your rental agreement. Do not arrange independent repairs without approval. Staff review replacement transport subject to local availability.'),
        'tyres': ('Tyre damage', 'Standard CDW excludes tyre and windscreen damage. Zero Excess Premium includes these items for permitted use. Roadside Plus supplies flat tyre assistance but does not pay for a replacement tyre.'),
        'theft': ('Vehicle theft', 'Report theft to police and ApexDrive immediately and retain the report number. Return all remaining keys. Zero Excess Premium includes a theft waiver subject to permitted-use conditions.'),
        'charging': ('Electric charging and return', 'Electric vehicles leave with a full battery and must be returned full under the Full-to-Full policy. Plan charging before return. Ask staff to document the battery level at both inspections.'),
        'charging-cable': ('Charging cable', 'A charging cable is supplied with each Electric rental. Check its presence at pickup and return it with the car. Missing cables are billed at documented replacement cost.'),
        'supercharging': ('Electric charging allowance', 'Electric category rentals include free Supercharging for the first 200 miles. This allowance does not waive the full-battery return requirement. Other charging expenses require staff clarification before purchase.'),
        'fuel-receipt': ('Fuel evidence', 'Keep the final fuel receipt and photograph the gauge. The return inspection checks the fuel level. If the gauge was not full at pickup, ask staff to amend the agreement before leaving.'),
        'deposit-release': ('Deposit release timing', 'The $200 deposit is a refundable pre-authorization, released after return inspection if there are no outstanding charges. The card issuer controls when available credit updates; ApexDrive cannot guarantee a bank processing date.'),
        'debit-documents': ('Debit card documentation', 'Debit cards require proof of a return flight ticket. The card and ticket must identify the primary renter. Staff verify eligibility at pickup; prepaid and anonymous cards are not accepted.'),
        'additional-driver': ('Registering another driver', 'Each additional driver costs $12 per day, must attend pickup with a valid license, and must meet the same age and license-tenure requirements as the primary driver. Unregistered drivers may not drive.'),
        'child-seat': ('Child seat fitting', 'Child safety seats cost $10 per day. Request the correct size in advance and provide the child age and weight. The renter must verify proper installation before driving; staff cannot guarantee a particular seat model.'),
        'accessibility': ('Accessibility requests', 'Contact staff before reserving to discuss access needs. Hand controls and wheelchair-accessible vehicles are not part of the standard fleet and cannot be promised by the assistant.'),
        'reservation-status': ('Reservation confirmation', 'This demonstration assistant cannot create a booking, charge a card or check live fleet availability. It may collect preferences and explain published terms. Only staff can issue a valid reservation confirmation.'),
        'quote-period': ('Quote calculation period', 'One rental day is a consecutive 24-hour period from pickup. Published category rates are in USD. Quotes must itemize selected protection, add-ons and applicable surcharges; the refundable deposit is separate from rental cost.'),
        'cancellation-late': ('Late cancellation', 'Cancellation is free until 24 hours before scheduled pickup. Within 24 hours, the cancellation fee is one base rental day of the selected category. Add-ons and insurance are not included in that cancellation fee.'),
        'no-show': ('Missed collection', 'A no-show without cancellation is charged one base rental day. Contact staff if you cannot collect. A missed collection does not automatically transfer the booking to the next day.'),
        'privacy': ('Customer privacy', 'Do not send full card numbers, identity-document scans or passwords in chat. Staff collect required identity and payment information at the counter through approved systems. Chat is for rental planning.'),
        'lost-property': ('Lost property', 'Contact the return branch with rental dates and a description of the item. Found items are held for 30 days. Collection requires identification; shipping is at the owner expense after staff agreement.')
    }
    documents.update(extra)
    for slug, (title, body) in documents.items():
        (root / (slug + '.md')).write_text(f'# {title}\n\nApexDrive fictional training business | Policy version 2026-10-01 | USD\n\n{body}\n', encoding='utf-8')
    print(f'Wrote {len(documents)} documents')


if __name__ == '__main__':
    main()
