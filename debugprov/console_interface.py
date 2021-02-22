from __future__ import unicode_literals

import sqlite3

from graphviz import Graph
from prompt_toolkit.shortcuts import confirm, prompt

from debugprov.node import Node
from debugprov.execution_tree_creator import ExecTreeCreator
from debugprov.top_down import TopDown
from debugprov.heaviest_first import HeaviestFirst
from debugprov.visualization import Visualization
from debugprov.provenance_enhancement import ProvenanceEnhancement
from debugprov.single_stepping import SingleStepping
from debugprov.divide_and_query import DivideAndQuery
from debugprov.validity import Validity

class CustomVisualization(Visualization):

    def name_for_node(self, node:Node):
        return " {} {} '{}'".format(str(node.ev_id),node.name,str(node.retrn))

    def navigate(self, node:Node):
        chds = node.childrens
        for n in chds:
            self.graph.edge(str(node.ev_id), str(n.ev_id), None, dir='forward')
            if n.validity == Validity.INVALID:
                self.graph.node(str(n.ev_id), self.name_for_node(n), fillcolor=self.INVALID_COLOR, style='filled')
            elif n.validity == Validity.VALID: 
                self.graph.node(str(n.ev_id), self.name_for_node(n), fillcolor=self.VALID_COLOR, style='filled')
            elif n.validity == Validity.UNKNOWN:  
                self.graph.node(str(n.ev_id), self.name_for_node(n))
            elif n.validity is Validity.NOT_IN_PROV:
                self.graph.node(str(n.ev_id), self.name_for_node(n), fillcolor=self.PROV_PRUNED_NODE_COLOR, style='filled')
            
        if len(chds) > 0:
            g = Graph()
            for c in chds:
                g.node(str(c.ev_id))
            g.graph_attr['rank']='same'
            self.graph.subgraph(g)

        for n in chds: 
            self.navigate(n)

class ConsoleInterface:

    DEFAULT_SQLITE_PATH = '.noworkflow/db.sqlite'
    NAVIGATION_STRATEGIES = [SingleStepping, TopDown, HeaviestFirst, DivideAndQuery] 

    def ask_db_path(self):
        self.db_path = prompt('Insert the path to the db.sqlite generated by noWorkFlow: ', default=self.DEFAULT_SQLITE_PATH)
        
    def select_nav_strategy(self):
        nav_names = [n.__name__ for n in self.NAVIGATION_STRATEGIES]
        print("Choose a navigation strategy: ")
        for idx,obj in enumerate(nav_names):
            print('[{}] - {}'.format(str(idx+1),obj))
        ans = prompt('> ')
        print(ans, type(ans))
        self.choosen_nav_strategy = self.NAVIGATION_STRATEGIES[int(ans)-1] 
        
    def ask_use_prov(self):
        return confirm('Do you want to use provenance enhancement? ')

    def ask_use_wrong_data(self):
        ans = 0
        while (ans != 1 and ans != 2 and ans != 3):
            print("How do you want to perform the enhancement? ")
            print('[1] - Use the last print as criterion')
            print('[2] - Use a wrong output as criterion')
            print('[3] - Select node as criterion')
            ans = int(prompt('> '))
        return ans

    def ask_wrong_data(self):
        print("Tell me which output data is wrong ")
        wrong_data = prompt('> ')
        return wrong_data

    def ask_output_file_name(self):
        out_filename = prompt('Output file name: ', default='exec_tree')
        return out_filename

    def run(self):
        self.db_path = self.DEFAULT_SQLITE_PATH
        try:
            cursor = sqlite3.connect(self.db_path).cursor()
            creator = ExecTreeCreator(cursor)
        except:
            raise Exception('Error reading database!')  
            import sys;sys.exit()
        exec_tree = creator.create_exec_tree()
        self.select_nav_strategy()
        nav = self.choosen_nav_strategy(exec_tree) 
        #use_prov = self.ask_use_prov()
        use_prov = False
        if use_prov:
            prov = ProvenanceEnhancement(exec_tree, cursor)
            strategy = self.ask_use_wrong_data() 
            if strategy == 1:
                # Slice Criterion: last print
                wrong_data_id = prov.get_last_print_evid()
                prov.enhance(wrong_data_id)
            elif strategy == 2:
                # Slice criterion: Wrong output (informed by user)
                wrong_data = self.ask_wrong_data()
                wrong_data_id = prov.get_wrong_data_evid(wrong_data)
                prov.enhance(wrong_data_id)
            elif strategy == 3:
                # Slice criterion: Node in tree (informed by user)
                tmp_vis = Visualization(exec_tree)
                tmp_vis.view_exec_tree('tmp_tree')
                print("Tell me which ID ")
                ev_id = int(prompt('> '))
                prov.enhance(ev_id)

        result_tree = nav.navigate()
        file_name = self.ask_output_file_name()
        vis = Visualization(result_tree)
        vis.view_exec_tree(file_name, show=True)
    