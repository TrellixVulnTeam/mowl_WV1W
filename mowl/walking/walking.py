from deprecated.sphinx import versionchanged

class WalkingModel():

    '''
    :param num_walks: Number of walks per node
    :type num_walks: int
    :param walk_length: Length of each walk
    :type walk_length: int
    :param workers: Number of threads to be used for computing the walks, defaults to 1'
    :type workers: int, optional
    '''
    def __init__(self, num_walks, walk_length, outfile, workers=1):
        self.num_walks = num_walks
        self.walk_length = walk_length
        self.workers = workers
        self.outfile = outfile


    # Abstract methods
    @versionchanged(version = "0.1.0", reason = "The method now can accept a list of entities to focus on when generating the random walks.")
    def walk(self, edges, nodes_of_interest = None):
        '''
        This method will generate random walks from a graph in the form of edgelist.

        :param edges: List of edges
        :type edges: :class:`mowl.projection.edge.Edge`
        :param nodes_of_interest: List of entity names to filter the generated walks. If a walk contains at least one word of interest, it will be saved into disk, otherwise it will be ignored.  If no list is input, all the nodes will be considered. Defaults to ``None``
        :type nodes_of_interest: list, optional
        '''
        
        raise NotImplementedError()
