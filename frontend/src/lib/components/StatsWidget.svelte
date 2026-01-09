<script>
	import { Zap, CheckCircle, Clock, Archive, Flame, TrendingUp } from 'lucide-svelte';

	export let stats = {
		total_captured: 0,
		total_consumed: 0,
		pending: 0,
		archived: 0,
		streak_days: 0,
		consumption_rate: 0
	};

	const statItems = [
		{ key: 'total_captured', label: 'Catturati', icon: Zap, gradient: 'from-violet-500 to-purple-500' },
		{ key: 'total_consumed', label: 'Consumati', icon: CheckCircle, gradient: 'from-emerald-500 to-green-500' },
		{ key: 'pending', label: 'In coda', icon: Clock, gradient: 'from-amber-500 to-orange-500' },
		{ key: 'archived', label: 'Archiviati', icon: Archive, gradient: 'from-slate-400 to-gray-500' },
		{ key: 'streak_days', label: 'Streak', icon: Flame, gradient: 'from-red-500 to-orange-500' },
		{ key: 'consumption_rate', label: 'Ratio', icon: TrendingUp, gradient: 'from-blue-500 to-cyan-500', suffix: '%' }
	];
</script>

<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
	{#each statItems as stat}
		<div class="stat-card group hover:scale-[1.02]">
			<div class="flex items-center justify-center gap-2 mb-2 opacity-60 group-hover:opacity-100 transition-opacity">
				<svelte:component this={stat.icon} class="w-4 h-4" />
			</div>
			<div class="stat-value bg-gradient-to-r {stat.gradient} bg-clip-text text-transparent">
				{stat.key === 'consumption_rate'
					? stats[stat.key]?.toFixed(0)
					: stats[stat.key] || 0}{stat.suffix || ''}
			</div>
			<div class="stat-label">{stat.label}</div>
		</div>
	{/each}
</div>
