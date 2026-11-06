(() => {
  const cover = document.querySelector('.globe-opening');
  const frame = document.querySelector('.global-frame');
  if (!cover || !frame) return;
  const reduced = matchMedia('(prefers-reduced-motion:reduce)').matches;
  const origin = 'https://global.residualinertia.com';
  const start = performance.now();
  // Atlas rows: Asia, Africa, North America, South America, Europe, Oceania, Antarctica.
  const countries = [
    'AF AM AZ BH BD BT BN KH CN CY GE HK IN ID IR IQ IL JP JO KZ KW KG LA LB MO MY MV MN MM NP KP OM PK PS PH QA SA SG KR LK SY TW TJ TH TL TR TM AE UZ VN YE',
    'DZ AO BJ BW BF BI CV CM CF TD KM CG CD DJ EG GQ ER SZ ET GA GM GH GN GW CI KE LS LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW SH ST SN SC SL SO ZA SS SD TZ TG TN UG EH ZM ZW',
    'AI AG AW BS BB BZ BM BQ VG CA KY CR CU CW DM DO SV GL GD GP GT HT HN JM MQ MX MS NI PA PR BL KN LC MF PM VC SX TT TC US VI',
    'AR BO BR CL CO EC FK GF GY PY PE SR UY VE',
    'AX AL AD AT BY BE BA BG HR CZ DK EE FO FI FR DE GI GR GG HU IS IE IM IT JE XK LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SJ SE CH UA GB VA',
    'AS AU CX CC CK FJ PF GU KI MH FM NR NC NZ NU NF MP PW PG PN WS SB TK TO TV UM VU WF',
    'AQ'
  ].map(group => new Set(group.split(' ')));
  function fromZone(zone) {
    if (zone.startsWith('Antarctica/')) return 6;
    if (zone.startsWith('Africa/')) return 1;
    if (zone.startsWith('Europe/') || zone === 'Atlantic/Reykjavik') return 4;
    if (/^(Australia|Pacific)\//.test(zone)) return zone === 'Pacific/Honolulu' ? 2 : 5;
    if (zone.startsWith('America/')) return /Argentina|Buenos_Aires|Sao_Paulo|Santiago|Bogota|Lima|Caracas|La_Paz|Montevideo|Asuncion|Guayaquil|Manaus|Recife|Belem|Fortaleza|Cayenne|Paramaribo|Guyana|Araguaina|Bahia$|Cuiaba|Porto_Velho|Rio_Branco|Maceio|Eirunepe|Santarem|Punta_Arenas|Cordoba|Mendoza|Catamarca|Jujuy/.test(zone) ? 3 : 2;
    return 0;
  }
  async function chooseLand() {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    let row = fromZone(zone);
    const stop = new AbortController();
    const timer = setTimeout(() => stop.abort(), 450);
    try {
      if (row !== 6) {
        const response = await fetch('https://residualinertia.com/cdn-cgi/trace', {
          signal:stop.signal, cache:'no-store', credentials:'omit', referrerPolicy:'no-referrer'
        });
        if (response.ok) {
          const country = /^loc=([A-Z]{2})\s*$/m.exec(await response.text())?.[1];
          const located = countries.findIndex(group => group.has(country));
          if (located >= 0) row = located;
        }
      }
    } catch { /* Device time zone is available offline. */ }
    finally { clearTimeout(timer); }
    if (!cover.isConnected) return;
    cover.style.setProperty('--land-position', (row * 100 / 6)+'%');
    cover.classList.add('land-ready');
  }
  cover.hidden = false;
  chooseLand();
  const front = cover.querySelector('.front'), back = cover.querySelector('.back');
  const positions = Array.from({length:97}, (_,i) => {
    const angle = i*Math.PI/48;
    const x = 40*Math.cos(angle), y = 21*Math.sin(angle);
    const tilt = -28*Math.PI/180;
    const dx = x*Math.cos(tilt)-y*Math.sin(tilt), dy = x*Math.sin(tilt)+y*Math.cos(tilt);
    return {transform:`translate3d(${dx}%,${dy}%,0) rotate(-30deg) scale(${.85+.15*Math.sin(angle)})`};
  });
  front.style.transform = positions[0].transform;
  if (!reduced) {
    const timing = {duration:4100,iterations:Infinity};
    const epoch = document.timeline.currentTime;
    for (const [track,a,b] of [[front,1,0],[back,0,1]]) {
      const travel = track.animate(positions,timing);
      const depth = track.animate([{opacity:a,easing:'steps(1,end)'},{opacity:b,offset:.5,easing:'steps(1,end)'},{opacity:a}],timing);
      if (epoch !== null) travel.startTime = depth.startTime = epoch;
    }
  }
  let closing = false;
  function finish() {
    if (closing) return;
    closing = true;
    window.removeEventListener('message', receive);
    clearTimeout(failsafe);
    if (reduced) { cover.remove(); return; }
    cover.classList.add('leaving');
    setTimeout(()=>cover.remove(),1050);
  }
  function receive(event) {
    if (event.origin !== origin || event.source !== frame.contentWindow) return;
    if (event.data === 'ri-globe:ready') setTimeout(finish,reduced ? 0 : Math.max(0,3000-(performance.now()-start)));
    if (event.data === 'ri-globe:error') finish();
  }
  const failsafe = setTimeout(finish,8500);
  window.addEventListener('message', receive);
  frame.contentWindow.postMessage('ri-globe:status',origin);
})();
