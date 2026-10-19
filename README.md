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
