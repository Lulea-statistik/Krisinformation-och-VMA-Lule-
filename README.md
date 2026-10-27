# Krisinformation och VMA – Luleå

Publik webbplats: https://lulea-statistik.github.io/Krisinformation-och-VMA-Lule-/

## Syfte
En källspårbar och geografiskt kontrollerad sammanställning av formella VMA och andra krishändelser med fokus på Luleå kommun.

## Historisk täckning
**Ingen fast startårsgräns.** Historiska artiklar finns dokumenterade åtminstone från 2015 i nationellt material och ett verifierat Luleå-VMA från november 2018. Äldre källmaterial kan finnas, men något fullständigt VMA-register har ännu inte verifierats.

- `data/historical.json`: manuellt verifierade historiska poster; varje post ska ha original-URL och dokumenterad status.
- `data/live.json`: reserverat för framtida automatiserad insamling. Detta får inte presenteras som verifierade aktiva varningar om uppdateringen är för gammal.
- VMA och redaktionella krisnyheter ska hållas åtskilda. Uppdateringar och Cancel inom samma incident ska grupperas.
- Geografiska träffar på Norrbottens län får **inte** utan kontroll räknas som Luleåhändelser.

## Källor
- [Krisinformation API v3](https://api.krisinformation.se/v3): `/v3/news`, `/v3/vmas`. News har `days` och `numberOfNewsArticles`, men ingen dokumenterad offset- eller kalenderårsbaserad paginering.
- [Sveriges Radios VMA API](https://vmaapi.sr.se/index.html): `/api/v3/alerts` beskriver aktiva varningar, identifierare och Cancel; inte ett historiskt sök-API.
- [Krisinformations arkiv 2015](https://www.krisinformation.se/nyheter/2015/) och [historiskt Luleå-VMA 2018](https://www.krisinformation.se/nyheter/2018/november/vma-lulea/).

## Säkerhetsregel
Projektet är inte en officiell varningskanal. Visa aldrig inaktuella VMA som aktiva. Visa officiell länk och senaste lyckade inläsningstid.

## Vägtrafikinformation och SMHI-vädervarningar

Sidan [Vägvarningar](https://lulea-statistik.github.io/Krisinformation-och-VMA-Lule-/vagvarningar.html) redovisar två separata källor:

- **Trafikverket Situation 1.5**: vägtrafikhändelser som olyckor, vägarbeten, avstängningar och hinder. Insamlingskod: `scripts/trafikverket_road.py`. Publicerad data: `data/trafikverket_road.json`. Regionalt urval: Norrbottens län (länskod 25).
- **SMHI JSON-varningar**: vädervarningsområden och varningsnivåer. Dessa representerar inte enskilda vägtrafikhändelser.

### Aktivera Trafikverkets API

1. Registrera ett konto och skapa en API-nyckel på [Trafikverkets datautbytesportal](https://data.trafikverket.se/).
2. Lägg in nyckeln som **Repository secret** med det exakta namnet `TRAFIKVERKET_API_KEY` under **Settings → Secrets and variables → Actions**.
3. Kör [Uppdatera Trafikverkets vägtrafikinformation](https://github.com/Lulea-statistik/Krisinformation-och-VMA-Lule-/actions/workflows/trafikverket-road.yml) via **Run workflow**.
4. Kontrollera att `data/trafikverket_road.json` innehåller `"status":"ok"`. Om `status` är `missing_api_key` är integrationen inte aktiverad.

**Viktigt:** Nyckeln får inte skrivas in i HTML, JavaScript, JSON eller repositoryfiler. Schemat kör var 15:e minut. Saknad nyckel visas uttryckligen som ej ansluten, inte som noll trafikstörningar. En API-nyckel och lyckad körning behövs innan data kan verifieras mot det riktiga Trafikverket-API:t.

Kartan visar endast Trafikverkets uttryckligen angivna WGS84-geometrier (EPSG:4326, GeoJSON longitud/latitud). Platsuppgifter utan verifierad WGS84-geometri finns endast i tabellen. Luleåalternativet är ett kartutsnitt, inte ett verifierat kommunurval.

