# Sveriges Radios VMA som kompletterande källa

## Datakällor
- https://vmaapi.sr.se/index.html (separat VMA API v3, Swagger)
- https://vmaapi.sr.se/releasenotes (uppdateringar; v3 rekommenderad)
- https://om.sverigesradio.se/vma (information om VMA; åtkomst kan variera)

## Verifierat i API-dokumentationen
- `GET /api/v3/alerts` hämtar aktiva varningar, inte en komplett årsbaserad historik.
- `GET /api/v3/alert/{identifier}` hämtar ett känt meddelande-ID.
- `GET /api/v3/alerts/feed.{format}` ger Atom/RSS.
- `status=Actual` = skarpt meddelande; `Exercise` = övning; `Test` = systemtest och ska aldrig publiceras.
- `msgType=Alert`, `Update`, `Cancel` måste hanteras.
- Meddelande-ID (`SRCAP-...`) är inte händelse-ID (`SRVMA-...`). Slå ihop uppdateringar inom samma incident.
- Prenumerationsendpointen har avvecklats; leverantören rekommenderar regelbundna hämtningar.

## Metod och publicering
1. Kör `scripts/check_sr_vma.py` för teknisk kontroll; den sparar **inte** meddelandetext, lokalisering eller incident-ID.
2. Klarlägg specifika återanvändnings-/lagringsvillkor för VMA API innan automatisk långsiktig arkivering eller återpublicering.
3. Skilj aktiva VMA från historiska VMA, andra krisnyheter och test/övning.
4. Filtrera geografiskt på fastställd kommunrelation, inte enbart fritext eller länstillhörighet.
5. För historisk tidsserie krävs separat kontrollerat källmaterial; historiken är ännu ofullständig.

Observera att Sveriges Radios generella Öppet API är en annan produkt och har restriktiva regler kring lagring. Dessa villkor kan inte utan vidare antas vara identiska för VMA API. Verifiera hos SR.
