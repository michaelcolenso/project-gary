<script lang="ts">
  const priorities = [
    'Dataset Catalog',
    'Dataset Profiler',
    'Decision Agent',
    'Buyer Agent',
    'Monetization Agent',
    'Opportunity Engine',
    'Opportunity Graph',
    'Dossier Generator',
    'Dashboard',
    'Outcomes Tracking'
  ];
</script>

<main class="min-h-screen bg-slate-950 px-8 py-12 text-slate-100">
  <section class="mx-auto max-w-5xl">
    <p class="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-300">OpportunityForge v1</p>
    <h1 class="mt-4 text-5xl font-bold tracking-tight">Bloomberg Terminal for public-data businesses.</h1>
    <p class="mt-6 max-w-3xl text-lg text-slate-300">
      Discover datasets, identify valuable decisions, map buyers, evaluate monetization, and generate auditable opportunity dossiers.
    </p>

    <div class="mt-10 grid gap-4 md:grid-cols-3">
      <div class="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 class="text-xl font-semibold">Dataset</h2>
        <p class="mt-2 text-slate-400">Fresh public data cataloged with provenance and profile metadata.</p>
      </div>
      <div class="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 class="text-xl font-semibold">Decision</h2>
        <p class="mt-2 text-slate-400">High-value decisions with stakes, urgency, frequency, and consequences.</p>
      </div>
      <div class="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 class="text-xl font-semibold">Revenue</h2>
        <p class="mt-2 text-slate-400">Buyer profiles and monetization blueprints that avoid ad-first thinking.</p>
      </div>
    </div>

    <section class="mt-12 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 class="text-2xl font-semibold">Build priorities</h2>
      <ol class="mt-4 grid gap-2 md:grid-cols-2">
        {#each priorities as priority, index}
          <li class="rounded-lg bg-slate-800 px-4 py-3 text-slate-200">{index + 1}. {priority}</li>
        {/each}
      </ol>
    </section>
  </section>
</main>
