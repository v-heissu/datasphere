<script>
	export let stats = {
		total_captured: 0,
		total_consumed: 0,
		pending: 0,
		archived: 0,
		streak_days: 0,
		consumption_rate: 0
	};
</script>

<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-primary-600">{stats.total_captured}</div>
		<div class="text-sm text-gray-500">Catturati</div>
	</div>

	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-green-600">{stats.total_consumed}</div>
		<div class="text-sm text-gray-500">Consumati</div>
	</div>

	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-yellow-600">{stats.pending}</div>
		<div class="text-sm text-gray-500">In coda</div>
	</div>

	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-gray-500">{stats.archived}</div>
		<div class="text-sm text-gray-500">Archiviati</div>
	</div>

	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-orange-500">{stats.streak_days}</div>
		<div class="text-sm text-gray-500">Streak giorni</div>
	</div>

	<div class="card p-4 text-center">
		<div class="text-3xl font-bold text-purple-600">{stats.consumption_rate.toFixed(0)}%</div>
		<div class="text-sm text-gray-500">Ratio</div>
	</div>
</div>
