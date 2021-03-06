from cool_ast.cool_ast import ProgramNode, ClassDeclarationNode, AttrDeclarationNode, FuncDeclarationNode
import visitors.visitor as visitor
from utils.semantic import Context, SemanticError, Type, ErrorType


class TypeBuilder:
    def __init__(self, context, errors):
        self.context = context
        self.current_type = None
        self.errors = errors
        self.check_node = None

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ProgramNode)
    def visit(self, node):

        _object = self.context.get_type('Object')
        _int = self.context.get_type('Int')
        _bool = self.context.get_type('Bool')
        _string = self.context.get_type('String')
        _io = self.context.get_type('IO')
        _self = self.context.get_type('SELF_TYPE')

        _object.define_method('abort', [], [], _object)
        _object.define_method('type_name', [], [], _string)
        _object.define_method('copy', [], [], _self)
        
        _io.set_parent(_object)
        _string.set_parent(_object)
        _int.set_parent(_object)
        _bool.set_parent(_object)

        _io.define_method('in_string', [], [], _string)
        _io.define_method('out_string', ['x'], [_string], _self)
        _io.define_method('in_int', [], [], _int)
        _io.define_method('out_int', ['x'], [_int], _self)

        _string.define_method('length', [], [], _int)
        _string.define_method('substr', ['index', 'length'], [_int, _int], _string)
        _string.define_method('concat', ['str'], [_string], _string)


        for declaration in node.declarations:
            self.visit(declaration)

        self.check_node = Check_Node('Object')
        
        cyclicHeritage =  self.CheckHeritageTree()
        
        if cyclicHeritage:
            self.errors.append('CyclicError: Cyclic heritage is not allowed')
    
        types = self.context.types
        main_type = None
        for type in types.values():
            if 'Main' == type.name:
                main_type = type
                break
        if main_type is not None:
            methods = main_type.methods
            main_method = None
            for m in methods:
                # if m.name == 'main' and len(m.param_names) == 0:
                if m.name == 'main':
                    main_method = m
                    break
            if main_method is None:
                self.errors.append('MainTypeError: Type Main does not have a main method or the main method have params') 
        else:
            self.errors.append("ProgramError: The program doesn't have a type Main")

        acker = OverrideACK(self.context,self.errors)
        acker.visit(node)
        
    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        self.current_type = self.context.get_type(node.id)

        if node.parent is not None:
            if node.parent in ("Int", "String", "Bool", "SELF_TYPE"):
                self.errors.append(f'TypeError: Class {node.id} cannot inherits from {node.parent}' )
            try:
                self.current_type.set_parent(self.context.get_type(node.parent))
            except SemanticError as e:
                self.errors.append(e.text)
        else:
            self.current_type.set_parent(self.context.get_type('Object'))

        # self_attr = AttrDeclarationNode('self', self.current_type.name)
        # self.visit(self_attr)

        for feature in node.features:
            self.visit(feature)

    @visitor.when(AttrDeclarationNode)
    def visit(self, node):
        try:
            t_attr = self.context.get_type(node.type)
        except SemanticError as e:
            self.errors.append(e.text)
            t_attr = ErrorType()
        try:
            self.current_type.define_attribute(node.id, t_attr)
        except SemanticError as e:
            self.errors.append(e.text)

    @visitor.when(FuncDeclarationNode)
    def visit(self, node):
        param_names = []
        param_types = []
        for name, typex in node.params:
            param_names.append(name)
            try:
                param_types.append(self.context.get_type(typex))
            except SemanticError as e:
                param_types.append(ErrorType())
                self.errors.append(e.text)

        try:
            return_type = self.context.get_type(node.type)
        except SemanticError as e:
            return_type = ErrorType()
            self.errors.append(e.text)

        self.current_type.define_method(node.id, param_names, param_types, return_type)

####################################################################
    def CheckHeritageTree(self):
        def CheckCyclicHeritage(n): #n is root, idealmente n = Object
            pending = [n]
            visited = {}
            while pending:
                node = pending.pop()
                try:
                    if visited[node]:
                        return True, visited
                except KeyError:
                    visited[node] = True, visited 
                                
                pending.extend(node.adj) 
            return False, visited
                
        gNodes = self.BuildGraph(self.context.get_type('Object'))
        
        visited = {}
        for n in gNodes:
            visited[n] = False
            
        for n in gNodes:
            if visited[n]:
                continue
            cycle, nVisited = CheckCyclicHeritage(n)
            if cycle:
                return True
            for node in nVisited:
                visited[node] = True
        
        return False
                
    def BuildGraph(self, rootType):
        #esto no deberia lanzar excepcion, a menos que haya hecho mal el bfs o algo.... :D
        _root = Check_Node(rootType.name)
        
        nodes = {}
        nodes[_root.name] = _root
        
        # l = self.context.types.keys()
        types = self.context.types
        for t in types.values(): # no se puede heredar de int ni de bool, y object lo hice a mano
            if t.name in ['Object']:
                continue
            try:
                _node = nodes[t.name]
            except:
                _node = Check_Node(t.name)
                nodes[t.name] = _node
            if t.parent is not None and t.parent.name not in ['Bool', 'int']:
                try:
                    nodes[t.parent.name].AddAdj(_node)
                except KeyError:
                    parentNode = Check_Node(t.parent.name,[_node])
                    nodes[t.parent.name] = parentNode
        return nodes.values()

class Check_Node:
    def __init__(self, name, adjuntos = []):
        self.name = name
        self.adj = []
        for t in adjuntos:
            self.adj.append(t)

    def AddAdj(self, node):
        if node in self.adj:
            raise Exception(f'{self.name} ya era adyacente a {node.name}')
        self.adj.append(node)

class OverrideACK:
    def __init__(self, context, errors):
        self.context = context
        self.current_type = None
        self.errors = errors

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ProgramNode)
    def visit(self, node):
        for declaration in node.declarations:
            self.visit(declaration)

    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        nodeType = self.context.get_type(node.id)
        self.current_type = nodeType

        for feature in node.features:
            self.visit(feature)

    @visitor.when(AttrDeclarationNode)
    def visit(self, node):
        try:
            attribute, owner = self.current_type.parent.get_attribute(node.id,self.current_type, False, True)
            self.errors.append(f'The attribute {attribute.name} is already defined in {owner.name}')
        except:
            pass

    @visitor.when(FuncDeclarationNode)
    def visit(self, node):
        current_method = self.current_type.get_method(node.id, self.current_type, False)
        try:
            method, owner = self.current_type.parent.get_method(node.id, self.current_type, False, get_owner=True)
            if method != current_method:
                self.errors.append(f'Function {node.id} is already defined in {owner.name}.')
        except:
            pass