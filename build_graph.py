import networkx as nx
from pygraphviz import AGraph
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from pyvis.network import Network
import os
class Watcher:
    DIRECTORY_TO_WATCH = os.getcwd()
    FILE_TO_WATCH = "master.dot"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):
    @staticmethod
    def on_modified(event):
        if event.is_directory:
            return None
        elif event.src_path.endswith(Watcher.FILE_TO_WATCH):
            generate_pyvis_html(event.src_path)

def generate_pyvis_html(dot_file_path):
    A = AGraph(string=open(dot_file_path).read())
    G = nx.DiGraph(A)

    nt = Network(notebook=True, width='100%', height='700px', directed=True)
    nt.from_nx(G)

    # Setup hover behavior to display connected nodes
    for node in G.nodes():
        connected_nodes = list(G.successors(node))
        connected_nodes.extend(G.predecessors(node))
        
        # Setting up the tooltip title here
        print("here>>",len(nt.nodes))
        for node_data in nt.nodes:
            if node_data['id'] == node:
                node_data['title'] = f'Connected to {", ".join(connected_nodes)}'
                break
    
    nt.show_buttons()
    nt.show("graph.html")

if __name__ == '__main__':
    generate_pyvis_html(Watcher.FILE_TO_WATCH)
    w = Watcher()
    w.run()
