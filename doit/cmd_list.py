from .cmd_base import DoitCmdBase, check_tasks_exist, subtasks_iter

opt_listall = {
    'name': 'subtasks',
    'short':'',
    'long': 'all',
    'type': bool,
    'default': False,
    'help': "list include all sub-tasks from dodo file"
    }

opt_list_quiet = {
    'name': 'quiet',
    'short': 'q',
    'long': 'quiet',
    'type': bool,
    'default': False,
    'help': 'print just task name (less verbose than default)'
    }

opt_list_status = {
    'name': 'status',
    'short': 's',
    'long': 'status',
    'type': bool,
    'default': False,
    'help': 'print task status (R)un, (U)p-to-date, (I)gnored'
    }

opt_list_private = {
    'name': 'private',
    'short': 'p',
    'long': 'private',
    'type': bool,
    'default': False,
    'help': "print private tasks (start with '_')"
    }

opt_list_dependencies = {
    'name': 'list_deps',
    'short': '',
    'long': 'deps',
    'type': bool,
    'default': False,
    'help': ("print list of dependencies "
             "(file dependencies only)")
    }

opt_disp_graph = {
    'name': 'disp_graph',
    'short': 'g',
    'long': 'graph',
    'type': bool,
    'default': False,
    'help': "display a dependency-graph with selected (or all) tasks (required networkx & matplotlib libs)."
    }

opt_template = {
    'name': 'template',
    'short': '',
    'long': 'template',
    'type': str,
    'default': None,
    'help': "display entries with template"
    }


class List(DoitCmdBase):
    doc_purpose = "list tasks from dodo file"
    doc_usage = "[TASK ...]"
    doc_description = None

    cmd_options = (opt_listall, opt_list_quiet, opt_list_status,
                   opt_list_private, opt_list_dependencies,
                   opt_disp_graph, opt_template)


    STATUS_MAP = {'ignore': 'I', 'up-to-date': 'U', 'run': 'R'}


    def _get_task_status(self, task):
        """print a single task"""
        # FIXME group task status is never up-to-date
        if self.dep_manager.status_is_ignore(task):
            task_status = 'ignore'
        else:
            # FIXME:'ignore' handling is ugly
            task_status = self.dep_manager.get_status(task, None)
        return self.STATUS_MAP[task_status]

    def _print_task(self, template, task, status, list_deps):
        """print a single task"""
        line_data = {'name': task.name, 'doc':task.doc}
        # FIXME group task status is never up-to-date
        if status:
            line_data['status'] = self._get_task_status(task)

        self.outstream.write(template.format(**line_data))

        # print dependencies
        if list_deps:
            for dep in task.file_dep:
                self.outstream.write(" -  %s\n" % dep)
            self.outstream.write("\n")

    @staticmethod
    def _list_filtered(tasks, filter_tasks, include_subtasks):
        """return list of task based on selected 'filter_tasks' """
        check_tasks_exist(tasks, filter_tasks)

        # get task by name
        print_list = []
        for name in filter_tasks:
            task = tasks[name]
            print_list.append(task)
            if include_subtasks:
                print_list.extend(subtasks_iter(tasks, task))
        return print_list


    def _list_all(self, include_subtasks):
        """list of tasks"""
        print_list = []
        for task in self.task_list:
            if (not include_subtasks) and task.is_subtask:
                continue
            print_list.append(task)
        return print_list

    def _prepare_graph(self, all_tasks_map, filter_task_names):
        """
        Construct a *networkx* graph of nodes (Tasks/Files/Wildcards) and their dependencies (file/wildcard, task/setup,calc).

        :param filter_task_names: If None, graph includes all tasks
        """
        import networkx as nx

        task_attributes = {
            'task_dep':     {'node_type':'task'},
            'setup_tasks':  {'node_type':'task', 'edge_type':'setup_dep'},
            'calc_dep':     {'node_type':'task'},
            'file_dep':     {'node_type':'file'},
            'wild_dep':     {'node_type':'wildcard'},
        }

        graph = nx.DiGraph()
        def add_graph_node(node, node_type, add_deps=False):
            if node in graph:
                return
            if node_type != 'task':
                graph.add_node(node, type=node_type)
            else:
                task = all_tasks_map[node]
                graph.add_node(node, type=node_type,
                               is_subtask=task.is_subtask,
                               status=self._get_task_status(task))
                if add_deps:
                    for attr, attr_kws in task_attributes.items():
                        for dname in getattr(task, attr):
                            dig_deps = filter_task_names is None or dname in filter_task_names
                            add_graph_node(dname, attr_kws['node_type'], add_deps=dig_deps)
                            graph.add_edge(node, dname, type=attr_kws.get('edge_type', attr))
                    ## Above loop cannot add targets
                    #    because they are reversed.
                    #
                    for dname in task.targets:
                        add_graph_node(dname, 'file')
                        graph.add_edge(dname, node, type='target')

        ## Add all named-tasks
        #    and their dependencies.
        #
        for tname in (filter_task_names or all_tasks_map.keys()):
            add_graph_node(tname, 'task', add_deps=True)

        return graph

    def _display_graph(self, graph, template):
        import networkx as nx
        from matplotlib import pyplot as plt

        def find_node_attr(g, attr, value):
            return [n for n,d in g.nodes_iter(data=True) if d[attr] == value]
        def find_edge_attr(g, attr, value):
            return [(n1,n2) for n1,n2,d in g.edges_iter(data=True) if d[attr] == value]

        node_type_styles = {
            'task':     { 'node_color': 'g', 'node_shape': 's'},
            'file':     { 'node_color': 'b', 'node_shape': 'o'},
            'wildcard': { 'node_color': 'c', 'node_shape': '8'},
        }
        dep_type_styles = {
            ## TASK-dependencies
            'task_dep': { 'edge_color': 'k', 'style': 'dotted'},
            'setup_dep':{ 'edge_color': 'm', },
            'calc_dep': { 'edge_color': 'g', },
            ## DATA-dependencies
            'file_dep': { 'edge_color': 'b', },
            'wild_dep': { 'edge_color': 'b', 'style': 'dashed'},
            'target':   { 'edge_color': 'c', },
        }

        pos = nx.spring_layout(graph, dim=2)
        for item_type, style in node_type_styles.items():
            nodes       = find_node_attr(graph, 'type', item_type)
            nx.draw_networkx_nodes(graph, pos, nodes,
                                   label=item_type, alpha=0.8,
                                   **style)
        for item_type, style in dep_type_styles.items():
            edges       = find_edge_attr(graph, 'type', item_type)
            edge_col    = nx.draw_networkx_edges(graph, pos, edges,
                                   label=item_type, alpha=0.5,
                                   **style)
            if edge_col:
                edge_col.set_label(None)    ## Remove duplicate label on DiGraph.
        labels = {n: (template.format(name=n, **d) if d['type'] == 'task' else n)
                       for n,d in graph.nodes_iter(data=True)}
        nx.draw_networkx_labels(graph, pos, labels)
        ax = plt.gca()
        ax.legend(scatterpoints=1, framealpha=0.5)
        #ax.set_frame_on(False)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        plt.subplots_adjust(0,0,1,1)

        plt.show()


    def _execute(self, subtasks=False, quiet=True, status=False,
                 private=False, list_deps=False, template=None,
                 disp_graph=False, pos_args=None):
        """List task generators, in the order they were defined.
        """
        filter_tasks = pos_args
        # dict of all tasks
        tasks = dict([(t.name, t) for t in self.task_list])

        if filter_tasks:
            # list only tasks passed on command line
            print_list = self._list_filtered(tasks, filter_tasks, subtasks)
        else:
            print_list = self._list_all(subtasks)

        # exclude private tasks
        if not private:
            print_list = [t for t in print_list if not t.name.startswith('_')]

        if disp_graph:
            if template is None:
                template = '{name}'
                if status:
                    template = '({status})' + template
            task_names = None
            if filter_tasks or not private:
                task_names = [task.name for task in print_list]

            graph = self._prepare_graph(tasks, task_names)
            self._display_graph(graph, template)
        else:
            # set template
            if template is None:
                max_name_len = 0
                if print_list:
                    max_name_len = max(len(t.name) for t in print_list)

                template = '{name:<' + str(max_name_len + 3) + '}'
                if not quiet:
                    template += '{doc}'
                if status:
                    template = '{status} ' + template
            template += '\n'

            # print list of tasks
            for task in sorted(print_list):
                self._print_task(template, task, status, list_deps)

        return 0
