"""
LEMS parser

@author: Gautham Ganapathy
@organization: Textensor (http://textensor.com)
@contact: gautham@textensor.com, gautham@lisphacker.org
"""

from xml.etree import ElementTree as xml
import os.path

from lems.model.simple import Dimension,Unit
from lems.base.parser import Parser
from lems.model.model import Model
from lems.base.errors import ParseError,ModelError
from lems.model.context import Context,Contextual
from lems.model.component import Component,ComponentType
from lems.model.parameter import Parameter
from lems.model.behavior import *
#Behavior,Regime,OnCondition,OnEvent,StateAssignment

def xmltolower(node):
    """ Converts the tag and attribute names in the given XML node and
    child nodes to lower case. To convert the entire tree, pass in the
    root.

    @param node: Node in an XML tree.
    @type node: xml.etree.Element """

    node.lattrib = dict()
    for key in node.attrib:
        node.lattrib[key.lower()] = node.attrib[key]
    for child in node:
        xmltolower(child)

class LEMSParser(Parser):
    """
    Parser for LEMS files
    """

    base_path = '.'
    """ Base path for the file being parsed
    @type: string """

    model = None
    """ Model built during parsing
    @type: lems.model.model.model """

    tag_parse_table = None
    """ Dictionary of xml tags to parse methods
    @type: dict(string -> function) """

    valid_children = None
    """ Dictionary mapping each tag to it's list of valid child tags.
    @type: dict(string -> string) """

    context_stack = []
    """ Stack of contexts used for handling nested contexts.
    @type: list(lems.model.context.Context) """

    current_context = None
    """ Currently active (being parsed) context.
    @type: lems.model.context.Context """

    component_type_stack = []
    """ Stack of component type objects used for handling nested
    component types.
    @type: list(lems.model.parameter.ComponentType) """

    current_component_type = None
    """ Component type object being parsed.
    @type: lems.model.parameter.ComponentType """

    current_regime = None
    """ Current behavior regime being parsed.
    @type: lems.model.behavior.Regime """

    current_event_handler = None
    """ Current event_handler being parsed.
    @type: lems.model.behavior.EventHandler """

    current_structure = None
    """ Current structure being parsed.
    @type: lems.model.structure.Structure """

    xml_node_stack = []
    """ XML node stack.
    @type: list(xml.etree.Element) """

    def push_context(self, context):
        self.context_stack = [context] + self.context_stack
        self.current_context = context

    def pop_context(self):
        if len(self.context_stack) == 0:
            self.raise_error('Context stack underflow')
        self.context_stack = self.context_stack[1:]
        if len(self.context_stack) == 0:
            self.current_context = None
        else:
            self.current_context = self.context_stack[0]
 
    def push_component_type(self, component_type):
        self.component_type_stack = [component_type] + \
                                    self.component_type_stack
        self.current_component_type = component_type

    def pop_component_type(self):
        if len(self.component_type_stack) == 0:
            self.raise_error('Component_Type stack underflow')
        self.component_type_stack = self.component_type_stack[1:]
        if len(self.component_type_stack) == 0:
            self.current_component_type = None
        else:
            self.current_component_type = self.component_type_stack[0]

    def init_parser(self):
        """
        Initializes the parser
        """
        
        self.model = Model()
        self.token_list = None
        self.prev_token_lists = None

        self.valid_children = dict()
        self.valid_children['lems'] = ['component', 'componenttype', 
                                       'defaultrun', 'dimension', 'include',
                                       'unit']
        self.valid_children['componenttype'] = ['behavior', 'behaviour',
                                                'child', 'children',
                                                'componentref',
                                                'exposure', 'eventport', 
                                                'fixed', 'link', 'parameter',
                                                'path', 'requirement',
                                                'structure', 'text']
        self.valid_children['behavior'] = ['derivedvariable',
                                           'oncondition', 'onentry',
                                           'onevent',
                                           'onstart', 'record',
                                           'run', 'show',
                                           'statevariable', 'timederivative']
        self.valid_children['oncondition'] = ['eventout', 'stateassignment']
        self.valid_children['onentry'] = ['eventout', 'stateassignment']
        self.valid_children['onevent'] = ['eventout', 'stateassignment']
        self.valid_children['onstart'] = ['eventout', 'stateassignment']
        self.valid_children['structure'] = ['childinstance',
                                            'eventconnection',
                                            'foreach',
                                            'multiinstantiate']

        self.tag_parse_table = dict()
        self.tag_parse_table['behavior'] = self.parse_behavior
        self.tag_parse_table['child'] = self.parse_child
        self.tag_parse_table['childinstance'] = self.parse_child_instance
        self.tag_parse_table['children'] = self.parse_children
        self.tag_parse_table['component'] = self.parse_component
        self.tag_parse_table['componentref'] = self.parse_component_ref
        self.tag_parse_table['componenttype'] = self.parse_component_type
        self.tag_parse_table['defaultrun'] = self.parse_default_run
        self.tag_parse_table['derivedvariable'] = self.parse_derived_variable
        self.tag_parse_table['dimension'] = self.parse_dimension
        self.tag_parse_table['eventconnection'] = self.parse_event_connection
        self.tag_parse_table['eventout'] = self.parse_event_out
        self.tag_parse_table['eventport'] = self.parse_event_port
        self.tag_parse_table['exposure'] = self.parse_exposure
        self.tag_parse_table['fixed'] = self.parse_fixed
        self.tag_parse_table['foreach'] = self.parse_foreach
        self.tag_parse_table['include'] = self.parse_include
        self.tag_parse_table['link'] = self.parse_link
        self.tag_parse_table['multiinstantiate'] = \
                                                 self.parse_multi_instantiate
        self.tag_parse_table['oncondition'] = self.parse_on_condition
        self.tag_parse_table['onevent'] = self.parse_on_event
        self.tag_parse_table['onstart'] = self.parse_on_start
        self.tag_parse_table['parameter'] = self.parse_parameter
        self.tag_parse_table['path'] = self.parse_path
        self.tag_parse_table['record'] = self.parse_record
        self.tag_parse_table['requirement'] = self.parse_requirement
        self.tag_parse_table['run'] = self.parse_run
        self.tag_parse_table['show'] = self.parse_show
        self.tag_parse_table['stateassignment'] = self.parse_state_assignment
        self.tag_parse_table['statevariable'] = self.parse_state_variable
        self.tag_parse_table['structure'] = self.parse_structure
        self.tag_parse_table['text'] = self.parse_text
        self.tag_parse_table['timederivative'] = self.parse_time_derivative
        self.tag_parse_table['unit'] = self.parse_unit

        def counter():
            count = 1
            while True:
                yield count
                count = count + 1
                
        self.id_counter = counter()
        """ Counter genertor for generating unique ids.
        @type: int """

    prefix = ''

    def process_nested_tags(self, node):
        """
        Process child tags.

        @param node: Current node being parsed.
        @type node: xml.etree.Element

        @raise ParseError: Raised when an unexpected nested tag is found.
        """

        #self.prefix += '  '

        for child in node:
            #print self.prefix, child.tag,
            #print child.attrib['name'] if 'name' in child.attrib else '',
            #print child.attrib['id'] if 'id' in child.attrib else ''

            self.xml_node_stack = [child] + self.xml_node_stack

            ctagl = child.tag.lower()

            if ctagl in self.tag_parse_table:
                self.tag_parse_table[ctagl](child)
            else:
                self.parse_component_by_typename(child, child.tag)

            self.xml_node_stack = self.xml_node_stack[1:]
            
        #self.prefix = self.prefix[2:]

    def resolve_typename(self, typename):
        """ 
        Resolves type name from the contex stack.

        @param typename: Name of the type to be resolved.
        @type typename: string

        @return: Component type corresponding to the type name or None if
        undefined.
        @rtype: lems.model.component.ComponentType
        """

        stack = self.context_stack
        found = False
        while stack != [] and (not found):
            if typename in stack[0].component_types:
                found = True
                
        if found:
            return stack[0].component_types[typename]
        else:
            return None

    def resolve_component_name(self, component_name):
        """ 
        Resolves component name from the contex stack.

        @param component_name: Name of the component to be resolved.
        @type component_name: string

        @return: Component corresponding to the name or None if undefined.
        @rtype: lems.model.component.Component
        """

        stack = self.context_stack
        found = False
        while stack != [] and (not found):
            if component_name in stack[0].components:
                found = True
                
        if found:
            return stack[0].components[component_name]
        else:
            return None

    def raise_error(self, message):
        s = 'Parser error in '

        self.xml_node_stack.reverse()
        if len(self.xml_node_stack) > 1:
            node = self.xml_node_stack[0]
            s += '<{0}'.format(node.tag)
            if 'name' in node.lattrib:
                s += ' name=\"{0}\"'.format(node.lattrib['name'])
            if 'id' in node.lattrib:
                s += ' id=\"{0}\"'.format(node.lattrib['id'])
            s += '>'

        for node in self.xml_node_stack[1:]:
            s += '.<{0}'.format(node.tag)
            if 'name' in node.lattrib:
                s += ' name=\"{0}\"'.format(node.lattrib['name'])
            if 'id' in node.lattrib:
                s += ' id=\"{0}\"'.format(node.lattrib['id'])
            s += '>'

        s += ':\n  ' + message

        raise ParseError(s)
    
        self.xml_node_stack.reverse()
        
        
    def get_model(self):
        """
        Returns the generated model.

        @return: The generated model.
        @rtype: lems.model.model.Model
        """
        
        return self.model

    def parse_behavior(self, node):
        """
        Parses <Behavior>

        @param node: Node containing the <Behaviour> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Behavior must be defined inside a ' +
                             'component type')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            name = ''

        self.current_context.add_behavior_profile(name)
        
        old_regime = self.current_regime
        self.current_regime = self.current_context.selected_behavior_profile.\
                              default_regime
        
        self.process_nested_tags(node)
        
        self.current_regime = old_regime

    ## def parse_build(self, node):
    ##     """
    ##     Parses <Build>

    ##     @param node: Node containing the <Build> element
    ##     @type node: xml.etree.Element
    ##     """

    ##     pass

    def parse_child(self, node):
        """
        Parses <Child>

        @param node: Node containing the <Child> element
        @type node: xml.etree.Element
        """
        
        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Child definitions can only be made in ' +
                             'a component type')
        
        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('<Child> must specify a name for the ' +
                             'reference.')

        if 'type' in node.lattrib:
            type = node.lattrib['type']
        else:
            self.raise_error('<Child> must specify a type for the ' +
                             'reference.')
            
        self.current_context.add_child_def(name, type)

    def parse_child_instance(self, node):
        """
        Parses <ChildInstance>

        @param node: Node containing the <ChildInstance> element
        @type node: xml.etree.Element
        """
        
        if self.current_structure == None:
            self.raise_error('Child instantiations can only be made within ' +
                             'a structure definition')

        if 'component' in node.lattrib:
            component = node.lattrib['component']
        else:
            self.raise_error('<ChildInstance> must specify a component '
                             'reference')

        self.current_structure.add_single_child_def(component)
    
    def parse_children(self, node):
        """
        Parses <Children>

        @param node: Node containing the <Children> element
        @type node: xml.etree.Element
        """
        
        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Children definitions can only be made in ' +
                             'a component type')
        
        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('<Children> must specify a name for the ' +
                             'reference.')

        if 'type' in node.lattrib:
            type = node.lattrib['type']
        else:
            self.raise_error('<Children> must specify a type for the ' +
                             'reference.')
            
        self.current_context.add_children_def(name, type)

    def parse_component_by_typename(self, node, type):
        """
        Parses components defined directly by component name.

        @param node: Node containing the <Component> element
        @type node: xml.etree.Element

        @param type: Type of this component.
        @type type: string

        @raise ParseError: Raised when the component does not have an id.
        """

        if self.current_context.context_type == Context.GLOBAL:
            # Global component instatiation
            if 'id' in node.lattrib:
                id = node.lattrib['id']
            else:
                self.raise_error('Component must have an id')
            
            type = node.tag

            component = Component(id, self.current_context, type, None)

            self.current_context.add_component(component)
            
        else:
            # Child instantiation

            if 'id' in node.lattrib:
                id = node.lattrib['id']
                type = node.tag
            else:
                id = node.tag
                type = '__type_inherited__'

            component = Component(id, self.current_context, type)

            self.current_context.add_child(component)
            
        for key in node.attrib:
            if key.lower() not in ['extends', 'id', 'type']:
                param = Parameter(key, '__dimension_inherited__')
                param.set_value(node.attrib[key])
                component.add_parameter(param)

        self.push_context(component.context)
        self.process_nested_tags(node)
        self.pop_context()

    def parse_component(self, node):
        """
        Parses <Component>

        @param node: Node containing the <ComponentType> element
        @type node: xml.etree.Element
        """

        if 'id' in node.lattrib:
            id = node.lattrib['id']
        else:            
            self.raise_error('Component must have an id')
        
        if 'type' in node.lattrib:
            type = node.lattrib['type']
        else:
            type = None

        if type == None:
            if 'extends' in node.lattrib:
                extends = node.lattrib['extends']
            else:
                self.raise_error('Component must have a type or must ' +
                                 'extend another component')
        else:
            extends = None

        component = Component(id, self.current_context, type, extends)
        self.current_context.add_component(component)

        for key in node.attrib:
            if key.lower() not in ['extends', 'id', 'type']:
                param = Parameter(key, '__dimension_inherited__')
                param.set_value(node.attrib[key])
                component.add_parameter(param)
                
        self.push_context(component.context)
        self.process_nested_tags(node)
        self.pop_context()

    def parse_component_ref(self, node):
        """
        Parses <ComponentRef>

        @param node: Node containing the <ComponentTypeRef> element
        @type node: xml.etree.Element
        """
        
        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Component references can only be defined in ' +
                             'a component type')
        
        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('<ComponentRef> must specify a name for the ' +
                             'reference.')

        if 'type' in node.lattrib:
            type = node.lattrib['type']
        else:
            self.raise_error('<ComponentRef> must specify a type for the ' +
                             'reference.')
            
        self.current_context.add_component_ref(name, type)
        
    def parse_component_type(self, node):
        """
        Parses <ComponentType>

        @param node: Node containing the <ComponentType> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when the component type does not have a
        name.
        """
        
        try:
            name = node.lattrib['name']
        except:
            self.raise_error('Component type must have a name')

        if 'extends' in node.lattrib:
            extends = node.lattrib['extends']
        else:
            extends = None

        component_type = ComponentType(name, self.current_context, extends)
        self.current_context.add_component_type(component_type)

        self.push_context(component_type.context)
        self.process_nested_tags(node)
        self.pop_context()

    def parse_default_run(self, node):
        """
        Parses <DefaultRun>

        @param node: Node containing the <DefaultRun> element
        @type node: xml.etree.Element
        """
        
        self.model.add_default_run(node.lattrib['component'])
    
    def parse_derived_variable(self, node):
        """
        Parses <DerivedVariable>

        @param node: Node containing the <DerivedVariable> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<DerivedVariable> must be defined inside a ' +
                             'behavior profile or regime')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('A derived variable must have a name')

        if 'exposure' in node.lattrib:
            exposure = node.lattrib['exposure']
        else:
            exposure = None

        if 'dimension' in node.lattrib:
            dimension = node.lattrib['dimension']
        else:
            dimension = None

        if 'value' in node.lattrib:
            value = node.lattrib['value']
        else:
            value = None

        if 'select' in node.lattrib:
            select = node.lattrib['select']
        else:
            select = None

        if 'reduce' in node.lattrib:
            reduce = node.lattrib['reduce']
        else:
            reduce = None

        self.current_regime.add_derived_variable(name, exposure, dimension,
                                                 value, select, reduce)
            

    def parse_dimension(self, node):
        """
        Parses <Dimension>

        @param node: Node containing the <Dimension> element
        @type node: xml.etree.Element

        @raise ParseError: When the name is not a string or if the
        dimension is not a signed integer.
        """
        
        dim = list()
        try:
            name = node.lattrib['name']
            for d in ['l', 'm', 't', 'i', 'k', 'c', 'n']:
                dim.append(int(node.lattrib.get(d, 0)))
        except:
            self.raise_error('Invalid dimensionality format')

        self.model.add_dimension(Dimension(name, dim[0], dim[1], dim[2],
                                           dim[3], dim[4], dim[4], dim[6]))
            
    def parse_event_out(self, node):
        """
        Parses <EventOut>

        @param node: Node containing the <EventOut> element
        @type node: xml.etree.Element
        """

        if self.current_event_handler == None:
            self.raise_error('<EventOut> must be defined inside an ' +
                             'event handler in a behavior profile or regime')

        if 'port' in node.lattrib:
            port = node.lattrib['port']
        else:
            self.raise_error('\'port\' attribute not provided for ' +
                             '<StateAssignment>')

        action = EventOut(port)

        self.current_event_handler.add_action(action)
        
    def parse_event_connection(self, node):
        """
        Parses <EventConnection>

        @param node: Node containing the <EventConnection> element
        @type node: xml.etree.Element
        """

        if self.current_structure == None:
            self.raise_error('<EventConnection> must be defined inside a ' +
                             'structure definition')

        if 'from' in node.lattrib:
            from_ = node.lattrib['from']
        else:
            self.raise_error('\'from\' attribute not provided for ' +
                             '<EventConnection>')

        if 'to' in node.lattrib:
            to = node.lattrib['to']
        else:
            self.raise_error('\'to\' attribute not provided for ' +
                             '<EventConnection>')

        self.current_structure.add_event_connection(from_, to)
        
    def parse_event_port(self, node):
        """
        Parses <EventPort>

        @param node: Node containing the <EventPort> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Event ports can only be defined in ' +
                             'a component type')
        
        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error(('<EventPort> must specify a name for the '
                              'event port'))

        if 'direction' in node.lattrib:
            direction = node.lattrib['direction']
        else:
            self.raise_error(('<EventPort> must specify a direction for the '
                              'event port'))

        direction = direction.lower()
        if direction != 'in' and direction != 'out':
            self.raise_error(('Event port direction must be \'in\' '
                              'or \'out\''))

        self.current_context.add_event_port(name, direction)

    def parse_exposure(self, node):
        """
        Parses <Exposure>

        @param node: Node containing the <Exposure> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when the exposure name is not
        being defined in the context of a component type.
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Exposure names can only be defined in ' +
                             'a component type')
        
        if 'name' in node.lattrib:
            self.current_context.add_exposure(node.lattrib['name'])

    def parse_fixed(self, node):
        """
        Parses <Fixed>

        @param node: Node containing the <Fixed> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when
        """

        try:
            parameter = node.lattrib['parameter']
        except:
            self.raise_error('Parameter to be fixed must be specified')

        try:
            value = node.lattrib['value']
        except:
            self.raise_error('Value to be fixed must be specified')

        if self.current_context.lookup_parameter(parameter) == None:
            self.current_context.add_parameter(Parameter(
                parameter, '__dimension_inherited__'))
        self.current_context.lookup_parameter(parameter).fix_value(value)

    def parse_foreach(self, node):
        """
        Parses <ForEach>

        @param node: Node containing the <ForEach> element
        @type node: xml.etree.Element
        """

        if self.current_structure == None:
            self.raise_error('<ForEach> can only be made within ' +
                             'a structure definition')

        if 'instances' in node.lattrib:
            target = node.lattrib['instances']
        else:
            self.raise_error('<ForEach> must specify a reference to target'
                             'instances')

        if 'as' in node.lattrib:
            name = node.lattrib['as']
        else:
            self.raise_error('<ForEach> must specify a name for the '
                             'enumerated target instances')

        old_structure = self.current_structure
        self.current_structure = self.current_structure.add_foreach(\
            name, target)

        self.process_nested_tags(node)
        
        self.current_structure = old_structure
    
    def parse_include(self, node):
        """
        Parses <Include>

        @param node: Node containing the <Include> element
        @type node: xml.etree.Element
        """

        if 'file' not in node.lattrib:
            self.raise_error('Include file must be specified.')

        path = self.base_path + '/' + node.lattrib['file']

        root = xml.parse(path).getroot()
        xmltolower(root)

        self.parse_root(root)

    def parse_link(self, node):
        """
        Parses <Link>

        @param node: Node containing the <Link> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Link variables can only be defined in ' +
                             'a component type')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('A name must be provided for <Link>')

        if 'type' in node.lattrib:
            type = node.lattrib['type']
        else:
            type = None

        self.current_context.add_link_var(name, type)

    def parse_multi_instantiate(self, node):
        """
        Parses <MultiInstantiate>

        @param node: Node containing the <MultiInstantiate> element
        @type node: xml.etree.Element
        """
        
        if self.current_structure == None:
            self.raise_error('Child instantiations can only be made within ' +
                             'a structure definition')

        if 'component' in node.lattrib:
            component = node.lattrib['component']
        else:
            self.raise_error('<MultiInstantiate> must specify a component '
                             'reference')

        if 'number' in node.lattrib:
            number = node.lattrib['number']
        else:
            self.raise_error('<MultiInstantiate> must specify a number')

        self.current_structure.add_multi_child_def(component, number)
    
    def parse_on_condition(self, node):
        """
        Parses <OnCondition>

        @param node: Node containing the <OnCondition> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<OnCondition> must be defined inside a ' +
                             'behavior profile or regime')

        if 'test' in node.lattrib:
            test = node.lattrib['test']
        else:
            self.raise_error('Test expression required for <OnCondition>')

        event_handler = OnCondition(test)
        
        self.current_event_handler = event_handler
        self.current_regime.add_event_handler(event_handler)
        
        self.process_nested_tags(node)
        
        self.current_event_handler = None
        
    def parse_on_entry(self, node):
        """
        Parses <OnEntry>

        @param node: Node containing the <OnEntry> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<OnEvent> must be defined inside a ' +
                             'behavior profile or regime')

        event_handler = OnEntry()
        
        self.current_event_handler = event_handler
        self.current_regime.add_event_handler(event_handler)
        
        self.process_nested_tags(node)
        
        self.current_event_handler = None
        
    def parse_on_event(self, node):
        """
        Parses <OnEvent>

        @param node: Node containing the <OnEvent> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<OnEvent> must be defined inside a ' +
                             'behavior profile or regime')

        if 'port' in node.lattrib:
            port = node.lattrib['port']
        else:
            self.raise_error('Port name required for <OnCondition>')

        event_handler = OnEvent(port)
        
        self.current_event_handler = event_handler
        self.current_regime.add_event_handler(event_handler)
        
        self.process_nested_tags(node)
        
        self.current_event_handler = None
        
    def parse_on_start(self, node):
        """
        Parses <OnStart>

        @param node: Node containing the <OnStart> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<OnEvent> must be defined inside a ' +
                             'behavior profile or regime')

        event_handler = OnStart()
        
        self.current_event_handler = event_handler
        self.current_regime.add_event_handler(event_handler)
        
        self.process_nested_tags(node)
        
        self.current_event_handler = None
        
    def parse_parameter(self, node):
        """
        Parses <Parameter>

        @param node: Node containing the <Parameter> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when the parameter does not have a name.
        @raise ParseError: Raised when the parameter does not have a
        dimension.
        """
        
        try:
            name = node.lattrib['name']
        except:
            self.raise_error('Parameter must have a name')

        try:
            dimension = node.lattrib['dimension']
        except:
            self.raise_error('Parameter must have a dimension')

        parameter = Parameter(name, dimension)

        self.current_context.add_parameter(parameter)

    def parse_path(self, node):
        """
        Parses <Path>

        @param node: Node containing the <Path> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Path variables can only be defined in ' +
                             'a component type')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('A name must be provided for <Path>')

        if 'value' in node.lattrib:
            value = node.lattrib['value']
        else:
            value = None

        self.current_context.add_path_var(name, value)

    def parse_record(self, node):
        """
        Parses <Record>

        @param node: Node containing the <Record> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<Record> must be only be used inside a ' +
                             'behavior profile or regime')

        if 'quantity' in node.lattrib:
            quantity = node.lattrib['quantity']
        else:
            self.raise_error('\'quantity\' attribute required for <Text>')

        if 'scale' in node.lattrib:
            scale = node.lattrib['scale']
        else:
            self.raise_error('\'scale\' attribute required for <Text>')

        if 'color' in node.lattrib:
            color  = node.lattrib['color']
        else:
            self.raise_error('\'color\' attribute required for <Text>')

        self.current_regime.add_record(quantity, scale, color)

    def parse_requirement(self, node):
        """
        Parses <Requirement>

        @param node: Node containing the <Requirement> element
        @type node: xml.etree.Element
        """

        pass

    def parse_run(self, node):
        """
        Parses <Run>

        @param node: Node containing the <Run> element
        @type node: xml.etree.Element
        """

        if self.current_regime == None:
            self.raise_error('<Run> must be defined inside a ' +
                             'behavior profile or regime')

        if 'component' in node.lattrib:
            component = node.lattrib['component']
        else:
            self.raise_error('<Run> must specify a target component')

        if 'variable' in node.lattrib:
            variable = node.lattrib['variable']
        else:
            self.raise_error('<Run> must specify a state variable')

        if 'increment' in node.lattrib:
            increment = node.lattrib['increment']
        else:
            self.raise_error('<Run> must specify an increment for the ' +
                             'state variable')

        if 'total' in node.lattrib:
            total = node.lattrib['total']
        else:
            self.raise_error('<Run> must specify a final value for the ' +
                             'state variable')

        self.current_regime.add_run(component, variable, increment, total)
            
    def parse_show(self, node):
        """
        Parses <Show>

        @param node: Node containing the <Show> element
        @type node: xml.etree.Element
        """

        pass
 
    def parse_state_assignment(self, node):
        """
        Parses <StateAssignment>

        @param node: Node containing the <StateAssignment> element
        @type node: xml.etree.Element
        """

        if self.current_event_handler == None:
            self.raise_error('<StateAssignment> must be defined inside an ' +
                             'event handler in a behavior profile or regime')

        if 'variable' in node.lattrib:
            variable = node.lattrib['variable']
        else:
            self.raise_error('\'variable\' attribute not provided for ' +
                             '<StateAssignment>')

        if 'value' in node.lattrib:
            value = node.lattrib['value']
        else:
            self.raise_error('\'value\' attribute not provided for ' +
                             '<StateAssignment>')

        action = StateAssignment(variable, value)

        self.current_event_handler.add_action(action)
        
        
    def parse_state_variable(self, node):
        """
        Parses <StateVariable>

        @param node: Node containing the <StateVariable> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when the state variable is not
        being defined in the context of a component type.
        """

        if self.current_regime == None:
            self.raise_error('<StateVariable> must be defined inside a ' +
                             'behavior profile or regime')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('A state variable must have a name')

        if 'exposure' in node.lattrib:
            exposure = node.lattrib['exposure']
        else:
            exposure = None

        if 'dimension' in node.lattrib:
            dimension = node.lattrib['dimension']
        else:
            self.raise_error('A state variable must have a dimension')

        self.current_regime.add_state_variable(name, exposure, dimension)
            
    def parse_structure(self, node):
        """
        Parses <Structure>

        @param node: Node containing the <Structure> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Structure must be defined inside a ' +
                             'component type')

        old_structure = self.current_structure
        self.current_structure = self.current_context.structure

        self.process_nested_tags(node)
        
        self.current_structure = old_structure

    def parse_text(self, node):
        """
        Parses <Text>

        @param node: Node containing the <Text> element
        @type node: xml.etree.Element
        """

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Text variables can only be defined in ' +
                             'a component type')

        if 'name' in node.lattrib:
            name = node.lattrib['name']
        else:
            self.raise_error('A name must be provided for <Text>')

        if 'value' in node.lattrib:
            value = node.lattrib['value']
        else:
            value = None

        self.current_context.add_text_var(name, value)

    def parse_time_derivative(self, node):
        """
        Parses <TimeDerivative>

        @param node: Node containing the <TimeDerivative> element
        @type node: xml.etree.Element

        @raise ParseError: Raised when the time derivative is not
        being defined in the context of a component type.
        """

        if self.current_regime == None:
            self.raise_error('<TimeDerivative> must be defined inside a ' +
                             'behavior profile or regime')

        if self.current_context.context_type != Context.COMPONENT_TYPE:
            self.raise_error('Time derivatives can only be defined in ' +
                             'a component type')

        if 'variable' in node.lattrib:
            name = node.lattrib['variable']
        else:
            self.raise_error('The state variable being differentiated wrt ' +
                             'time must be specified')

        if 'value' in node.lattrib:
            value = node.lattrib['value']
        else:
            self.raise_error('The time derivative expression must be ' +
                             'provided')

        self.current_regime.add_time_derivative(name, value)

    def parse_unit(self, node):
        """
        Parses <Unit>

        @param node: Node containing the <Unit> element
        @type node: xml.etree.Element

        @raise ParseError: When the name is not a string or the unit
        specfications are incorrect.

        @raise ModelError: When the unit refers to an undefined dimension.
        """

        try:
            symbol = node.lattrib['symbol']
            dimension = node.lattrib['dimension']
        except:
            self.raise_error('Unit must have a symbol and dimension.')

        if 'powten' in node.lattrib:
            pow10 = int(node.lattrib['powten'])
        else:
            pow10 = 0

        self.model.add_unit(Unit(symbol, dimension, pow10))
    
    def parse_root(self, node):
        """
        Parse the <lems> (root) element of a LEMS file
        
        @param node: Node containing the <LEMS> element
        @type node: xml.etree.Element
        """
        
        if node.tag.lower() != 'lems':
            self.raise_error('Not a LEMS file')

        self.xml_node_stack = [node] + self.xml_node_stack
        self.process_nested_tags(node)
        self.xml_node_stack = self.xml_node_stack[1:]
            
    def parse_file(self, filename):
        """
        Parse a LEMS file and generate a LEMS model

        @param filename: Path to the LEMS file to be parsed
        @type filename: string
        """

        root = xml.parse(filename).getroot()
        xmltolower(root)
        
        self.base_path = os.path.dirname(filename)
        if self.base_path == '':
            self.base_path = '.'

        context = Context('__root_context__', self.current_context)
        if self.model.context == None:
            self.model.context = context

        self.push_context(context)

        self.parse_root(root)

        self.pop_context()


    def parse_string(self, str):
        pass
