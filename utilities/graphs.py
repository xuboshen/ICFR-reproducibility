import matplotlib.pyplot as plt

def epsilon_graph(results, xaxis = 'iterations', ybottom = 0):
	"""
	Draw graph for the epsilon from the data obtained from a run of SCFR.
	"""

	iteration_counts = list(map(lambda el: el['iteration_number'], results['graph_data']))
	durations = list(map(lambda el: el['duration'], results['graph_data']))
	cum_durations = [sum(durations[:i]) for i in range(len(durations))]
	epsilons_graph = list(map(lambda el: max(0, -min(el['epsilon'])), results['graph_data']))
	
	if xaxis == 'iterations':
		plt.plot(iteration_counts, epsilons_graph)
		plt.xlabel("Iteration")
	elif xaxis == 'time':
		plt.plot(cum_durations, epsilons_graph)
		plt.xlabel("Time")

	plt.ylabel("Epsilon")
	plt.ylim(bottom = ybottom)
	plt.show()

def comparative_epsilon_graph(results_array, delta_utility = 1, max_social_welfare = 1,
							  xaxis = 'iterations', yaxis = 'epsilon',
							  xlims = None, ylims = None, legend = None):
	"""
	Draw graph for the epsilons from the data obtained from multiple runs of SCFR in a single graph.
	"""

	if legend == None:
		legend = ["Result " + str(i+1) for i in range(len(results_array))]

	for (i, res) in enumerate(results_array):
		iteration_counts = list(map(lambda el: el['iteration_number'], res['graph_data']))
		durations = list(map(lambda el: el['duration'], res['graph_data']))
		cum_durations = [sum(durations[:i]) for i in range(len(durations))]
		epsilons_graph = list(map(lambda el: max(0, -min(el['epsilon'])) / delta_utility, res['graph_data']))
		sw_graph = list(map(lambda el: sum(el['utility']) / max_social_welfare, res['graph_data']))
		if yaxis == 'epsilon':
			ydata = epsilons_graph
		elif yaxis == 'social_welfare':
			ydata = sw_graph
		if xaxis == 'iterations':
			xdata = iteration_counts
		elif xaxis == 'time':
			xdata = cum_durations
		plt.plot(xdata, ydata)

	if yaxis == 'epsilon':
		plt.ylabel("Epsilon [%]")
	elif yaxis == 'social_welfare':
		plt.ylabel("Social welfare [%]")
	if xaxis == 'iterations':
		plt.xlabel("Iteration")
	elif xaxis == 'time':
		plt.xlabel("Time [s]")

	plt.legend(legend, bbox_to_anchor = (1.05, 1), loc = 2)
	
	if xlims != None:
		plt.xlim(xlims)
	if ylims != None:
		plt.ylim(ylims)
	plt.show()

def graphs_from_cfr_results(results):
	"""
	Draw graphs from the data obtained from a run of SCFR.
	"""

	absolute_joint_size_graph = list(map(lambda el: el['absolute_joint_size'], results['graph_data']))
	relative_joint_size_graph = list(map(lambda el: el['relative_joint_size'], results['graph_data']))
	max_plan_frequency = list(map(lambda el: el['max_plan_frequency'], results['graph_data']))
	iteration_counts = list(map(lambda el: el['iteration_number'], results['graph_data']))
	
	epsilon_graph(results)

	plt.plot(iteration_counts, absolute_joint_size_graph)
	plt.ylabel("Absolute joint size")
	plt.xlabel("Iteration")
	plt.show()
	plt.plot(iteration_counts, relative_joint_size_graph)
	plt.ylabel("Relative joint size")
	plt.xlabel("Iteration")
	plt.show()
	plt.plot(iteration_counts, max_plan_frequency)
	plt.ylabel("Most frequent joint plan")
	plt.xlabel("Iteration")
	plt.show()