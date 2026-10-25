/* Presentation-only controller. This module never calls a simulation or data API. */
(() => {
  'use strict';
  const experience = document.querySelector('#experience');
  const commandCenter = document.querySelector('#command-center');
  const motionButton = document.querySelector('#motion-toggle');
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  // Routes position their content explicitly, including on browser reload.
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  let userReduced = false;
  try { userReduced = localStorage.getItem('phantomshield-reduced-motion') === 'true'; } catch {}
  let media, context, storyTrigger, appImport, dashboard = false, initialized = false;
  const reduced = () => preference.matches || userReduced;
  const stageNames = ['network', 'deception', 'detection'];

  function updateMotionControl() {
    const off = reduced();
    document.documentElement.classList.toggle('motion-off', off);
    experience.classList.toggle('motion-paused', off || dashboard || document.hidden);
    motionButton.textContent = preference.matches ? 'Motion: reduced by system' : off ? 'Motion: off' : 'Motion: on';
    motionButton.setAttribute('aria-pressed', String(off));
    motionButton.setAttribute('aria-label', preference.matches ? 'Reduced motion is enabled by your system' : off ? 'Enable cinematic motion' : 'Disable cinematic motion');
    motionButton.disabled = preference.matches;
  }

  function markStage(index) {
    document.querySelectorAll('.stage-nav [data-stage]').forEach(link => {
      if (link.dataset.stage === stageNames[index]) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
    document.querySelector('.theater-status').textContent = ['NETWORK MAPPED', 'DECOYS DEPLOYED', 'INTRUSION DETECTED'][index];
  }

  function clearAnimations() {
    media?.revert(); context?.revert();
    media = context = storyTrigger = null;
    experience.classList.remove('motion-ready', 'mobile-motion');
    document.querySelectorAll('.story-chapter').forEach(chapter => chapter.removeAttribute('aria-hidden'));
  }

  function initAnimations() {
    clearAnimations(); updateMotionControl();
    if (reduced() || !window.gsap || !window.ScrollTrigger) return;
    const { gsap, ScrollTrigger } = window;
    gsap.registerPlugin(ScrollTrigger);
    ScrollTrigger.config({ ignoreMobileResize: true });
    context = gsap.context(() => {
      const intro = gsap.timeline({ defaults: { ease: 'power3.out' } });
      intro.from('.reveal-line > span', { yPercent: 105, duration: 1.05, stagger: 0.13 }, 0.1)
        .from('.hero-enter', { y: 15, autoAlpha: 0, duration: 0.8, stagger: 0.08 }, 0.35)
        .from('.shield-scene', { scale: 0.94, opacity: 0, duration: 1.25 }, 0.15)
        .from('.hero-float', { y: 14, opacity: 0, duration: 0.9, stagger: 0.2 }, 0.8);
      gsap.from('.defense-intro > *', { y: 22, autoAlpha: 0, duration: 0.8, stagger: 0.12,
        scrollTrigger: { trigger: '.exp-defense', start: 'top 85%', once: true } });
      gsap.from('.command-preview', { y: 42, autoAlpha: 0, duration: 1,
        scrollTrigger: { trigger: '.command-preview', start: 'top 90%', once: true } });
    }, experience);
    media = gsap.matchMedia();
    media.add('(min-width: 851px) and (min-height: 700px)', () => {
      experience.classList.add('motion-ready');
      const chapters = gsap.utils.toArray('.story-chapter');
      const edges = gsap.utils.toArray('.net-edges path');
      const traces = gsap.utils.toArray('.net-trace path');
      gsap.set(chapters, { autoAlpha: 0 }); gsap.set(chapters[0], { autoAlpha: 1 });
      gsap.set('.net-node', { opacity: 0.16 });
      gsap.set(edges, { strokeDasharray: 1, strokeDashoffset: 1 });
      gsap.set('.decoy-tags, .net-trace, .detected-ring, .illustrated-alert', { autoAlpha: 0 });
      gsap.set(traces, { strokeDasharray: 1, strokeDashoffset: 1 });
      let current = -1;
      const timeline = gsap.timeline({ defaults: { ease: 'none' }, scrollTrigger: {
        id: 'phantom-story', trigger: '.sequence-scene', start: 'top top',
        end: () => '+=' + Math.round(window.innerHeight * 3.5),
        scrub: 0.7, pin: true, anticipatePin: 1, invalidateOnRefresh: true,
        onUpdate(self) {
          const index = self.progress < 0.3 ? 0 : self.progress < 0.61 ? 1 : 2;
          if (current !== index) {
            current = index; markStage(index);
            chapters.forEach((c, i) => c.setAttribute('aria-hidden', String(i !== index)));
          }
        }
      }});
      timeline.addLabel('network', 0)
        .to('.net-node', { opacity: 1, stagger: 0.11, duration: 0.65 }, 0.15)
        .to(edges, { strokeDashoffset: 0, stagger: 0.12, duration: 0.8 }, 0.2)
        .to(chapters[0], { autoAlpha: 0, y: -15, duration: 0.3 }, 2.05)
        .fromTo(chapters[1], { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.4 }, 2.35)
        .addLabel('deception', 2.6)
        .to('.decoy-tags', { autoAlpha: 1, duration: 0.5 }, 2.65)
        .from('.decoy-tags > g', { y: 10, stagger: 0.2, duration: 0.4 }, 2.65)
        .to(chapters[1], { autoAlpha: 0, y: -15, duration: 0.3 }, 4.5)
        .fromTo(chapters[2], { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.4 }, 4.8)
        .addLabel('detection', 5)
        .to('.net-trace', { autoAlpha: 1, duration: 0.05 }, 5)
        .to(traces[0], { strokeDashoffset: 0, duration: 0.85 }, 5)
        .to(traces[1], { strokeDashoffset: 0, duration: 0.6 }, 5.8)
        .to(traces[2], { strokeDashoffset: 0, duration: 0.6 }, 6.35)
        .to('.target-node rect, [data-name="application"] rect', { stroke: '#f18393', fill: '#291c28', duration: 0.4 }, 5.85)
        .to('.detected-ring', { autoAlpha: 0.7, duration: 0.4 }, 6.2)
        .fromTo('.illustrated-alert', { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4 }, 6.7)
        .to('.sequence-progress i', { scaleX: 1, duration: 7.6 }, 0)
        .to({}, { duration: 0.5 }, 7.1);
      storyTrigger = timeline.scrollTrigger;
      markStage(0);
      gsap.to('.hero-orbit-bg', { y: 100, ease: 'none', scrollTrigger: { trigger: '.exp-hero', start: 'top top', end: 'bottom top', scrub: 1 } });
      gsap.to('.shield-scene', { y: 65, ease: 'none', scrollTrigger: { trigger: '.exp-hero', start: 'top top', end: 'bottom top', scrub: 1 } });
      return () => { experience.classList.remove('motion-ready'); storyTrigger = null; chapters.forEach(c => c.removeAttribute('aria-hidden')); };
    });
    media.add('(max-width: 850px), (max-height: 699px)', () => {
      experience.classList.add('mobile-motion');
      gsap.utils.toArray('.story-chapter').forEach((chapter, index) => {
        gsap.from(chapter.children, { y: 12, autoAlpha: 0, duration: 0.5, stagger: 0.04,
          scrollTrigger: { trigger: chapter, start: 'top 88%', once: true, onEnter: () => markStage(index) } });
      });
      const traces = gsap.utils.toArray('.net-trace path');
      gsap.set('.net-edges path, .net-trace path', { strokeDasharray: 1, strokeDashoffset: 1 });
      const mobileTimeline = gsap.timeline({ defaults: { ease: 'none' }, scrollTrigger: {
        trigger: '.network-theater', start: 'top 80%', end: 'bottom 35%', scrub: 0.3
      }});
      mobileTimeline.from('.net-node', { opacity: 0.25, stagger: 0.05, duration: 0.4 }, 0)
        .to('.net-edges path', { strokeDashoffset: 0, stagger: 0.04, duration: 0.35 }, 0)
        .from('.decoy-tags', { autoAlpha: 0, duration: 0.2 }, 0.4)
        .to(traces, { strokeDashoffset: 0, stagger: 0.12, duration: 0.35 }, 0.6)
        .from('.detected-ring, .illustrated-alert', { autoAlpha: 0, duration: 0.2 }, 1);
      return () => experience.classList.remove('mobile-motion');
    });
    ScrollTrigger.refresh();
  }

  function goToStage(name, behavior = reduced() ? 'instant' : 'smooth') {
    const index = stageNames.indexOf(name);
    if (index < 0) return;
    if (storyTrigger) {
      // Anchor into the held portion of each chapter, away from crossfades.
      const fractions = [0.16, 0.45, 0.95];
      window.scrollTo({ top: storyTrigger.start + (storyTrigger.end - storyTrigger.start) * fractions[index], behavior });
    } else document.getElementById(name).scrollIntoView({ behavior, block: 'start' });
  }

  async function route() {
    const nextDashboard = location.hash === '#dashboard';
    if (initialized && nextDashboard === dashboard) return;
    initialized = true; dashboard = nextDashboard;
    if (dashboard) clearAnimations();
    experience.hidden = dashboard; commandCenter.hidden = !dashboard;
    document.body.dataset.view = dashboard ? 'dashboard' : 'story';
    document.title = dashboard ? 'PhantomShield · Command center' : 'PhantomShield · See the unseen.';
    updateMotionControl();
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (dashboard) {
      try { await (appImport ||= import('/app.js')); }
      catch {
        appImport = null;
        document.querySelector('#app').innerHTML = '<div class="loading"><h1>Command center could not load</h1><p>Check that the local server is running, then reload.</p><button onclick="location.reload()">Retry</button></div>';
      }
      document.querySelector('#app h1')?.setAttribute('tabindex', '-1');
      document.querySelector('#app h1')?.focus({ preventScroll: true });
    } else {
      initAnimations();
      const anchor = location.hash.slice(1);
      if (stageNames.includes(anchor)) goToStage(anchor, 'instant');
      else if (anchor === 'defense') document.querySelector('#defense').scrollIntoView({ behavior: 'instant' });
    }
  }

  document.addEventListener('click', event => {
    const homeLink = event.target.closest('a[href="#threat"]');
    if (homeLink && !dashboard) {
      event.preventDefault(); history.replaceState(null, '', '#threat');
      window.scrollTo({ top: 0, behavior: reduced() ? 'instant' : 'smooth' });
    }
    const stageLink = event.target.closest('[data-stage]');
    if (stageLink && !dashboard) {
      event.preventDefault();
      history.replaceState(null, '', '#' + stageLink.dataset.stage);
      goToStage(stageLink.dataset.stage);
    }
    if (event.target.closest('[data-intro]')) location.hash = 'threat';
  });
  motionButton.addEventListener('click', () => {
    userReduced = !userReduced;
    try { localStorage.setItem('phantomshield-reduced-motion', String(userReduced)); } catch {}
    initAnimations();
  });
  preference.addEventListener('change', () => { if (!dashboard) initAnimations(); else updateMotionControl(); });
  document.addEventListener('visibilitychange', updateMotionControl);
  window.addEventListener('hashchange', route);
  route();
})();
