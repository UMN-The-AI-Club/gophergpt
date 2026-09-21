from langgraph.graph import StateGraph

class BaseStateAgent():
    def __init__(self, state_schema: dict):
        self.state_schema = state_schema
        self.workflow = StateGraph(state_schema)
        self.compiled_graph = None

    def initworkflow(self):
        '''Define the workflow of the agent here.'''
        raise NotImplementedError("Subclasses must implement the '__initworkflow__' method.")

    def __compilegraph__(self):
        '''Compile the graph, and enable it for execution'''
        try:
            self.initworkflow()
        except Exception as e:
            raise ValueError("Workflow is not defined. Create and call 'initworkflow' first.")

        self.compiled_graph = self.workflow.compile()
        print("Agent Graph has been compiled successfully.")

    def get_graph_runnable(self):
        if not self.compiled_graph:
            try:
                self.__compilegraph__()
            except Exception as e:
                raise ValueError("Graph Compile Error! Cannot return runnable.")
        return self.compiled_graph

    def force_compile(self):
        '''Force compile the graph, even if it is already compiled.'''
        self.compiled_graph = self.__compilegraph__()
        return self

    def stream_agent(self, messages):
        if not self.compiled_graph:
            try:
                self.__compilegraph__()
            except Exception as e:
                raise ValueError("Graph Compile Error! Cannot stream agent.")

        for event in self.compiled_graph.stream(messages):
            for value in event.values():
                yield value["messages"][-1].content

    async def invoke_agent(self, messages) -> dict:
        # return final state of graph.
        if not self.compiled_graph:
            try:
                self.__compilegraph__()
            except Exception as e:
                raise ValueError("Graph Compile Error! Cannot invoke agent.")

        graph_output = await self.compiled_graph.ainvoke(messages, {"recursion_limit": 15})
        return graph_output  # returns full final state of the graph.
