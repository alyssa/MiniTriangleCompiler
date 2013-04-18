import imp
import marshal
import os
import pprint
import struct
import sys
import time
import types

from byteplay import *

import ast
import parser
import scanner


class CodeGenError(Exception):
    """ Code Generator Error """
    def __init__(self, tree, expected):        
        self.tree = tree
        self.expected = expected

    def __str__(self):
        return 'Error at ast node: %s expected: %s' % (str(self.tree), str(self.expected))


class CodeGen(object):
    """ CodeGen """
    def __init__(self, tree):
        self.tree = tree
        self.code = []
       # self.env  = {}
        self.env  = []
        self.scope_count = 0

    def generate(self):
        """ start of appending bytecode. turns bytecode into callable func """
        if type(self.tree) is not ast.Program:
            raise CodeGenError(self.tree, ast.Program)
        if type(self.tree.command) is not ast.LetCommand:
            raise CodeGenError(self.tree.command, ast.LetCommand)
        
        self.push_stack()
        self.push_env()
        
        self.gen_command(self.tree.command)

        self.append_code((LOAD_CONST, None))
        self.append_code((RETURN_VALUE, None))
        
        func_code = self.pop_stack()
        self.pop_env()
        
        code_obj = Code(func_code, [], [], False, False, False, 'gencode', '', 0, '')
        code = code_obj.to_code()
        func = types.FunctionType(code, globals(), 'gencode')
        
        return func
        
    def gen_command(self, tree):
        """ given a general command and propagate to appropriate command func """
        if type(tree) is ast.AssignCommand:
            return self.gen_assign_command(tree)
        elif type(tree) is ast.CallCommand:
            return self.gen_call_command(tree)
        elif type(tree) is ast.SequentialCommand:
            return self.gen_seq_command(tree)
        elif type(tree) is ast.IfCommand:
            return self.gen_if_command(tree)
        elif type(tree) is ast.WhileCommand:
            return self.gen_while_command(tree)
        elif type(tree) is ast.LetCommand:
            return self.gen_let_command(tree)
        elif type(tree) is ast.ReturnCommand:
            return self.gen_return_command(tree)
        else:
            raise CodeGenError(tree, ast.Command)

    def gen_return_command(self, tree):
        """ generate bytecode fo a return command """
        expr = self.gen_expression(tree.expression)
        self.append_code((RETURN_VALUE, None))

    def gen_declaration(self, tree):
        """ given a general decl and propagate to appropriate decl func """
        if type(tree) is ast.VarDeclaration:
            curr_ident = self.add_to_env(tree.identifier)
            self.append_code((LOAD_CONST, None))
            self.append_code((STORE_FAST, curr_ident))
        elif type(tree) is ast.ConstDeclaration:
            curr_ident = self.add_to_env(tree.identifier)
            self.gen_expression(tree.expression)
            self.append_code((STORE_FAST, curr_ident))
        elif type(tree) is ast.SequentialDeclaration:
            self.gen_declaration(tree.decl1)
            self.gen_declaration(tree.decl2)
        elif type(tree) is ast.FunctionDeclaration:
            self.push_stack()
            self.push_env()
            func_ident = tree.name

            param = self.populate_param_list(tree.param)

            # load params into current environment
            for p in param:
                self.add_to_env(p)

            self.gen_command(tree.command)

            func_code = self.pop_stack()
            self.pop_env()
            
            code_obj = Code(func_code, [], param, False, False, False, 'gencode', '', 0, '')
            self.append_code((LOAD_CONST, code_obj))
            self.append_code((MAKE_FUNCTION, 0))
            self.append_code((STORE_FAST, func_ident))

    def populate_param_list(self, tree):
        """ recursively go through param/SequentialParameter to build list of param names """
        param_list = []
        self.populate_param_list_recur(tree, param_list)
        return param_list

    def populate_param_list_recur(self, tree, param_list):
        """ helper method for populate_param_list """
        if type(tree) == ast.Parameter:
            param_list.append(tree.argname)
        elif type(tree) == ast.SequentialParameter:
            self.populate_param_list_recur(tree.param1, param_list)
            self.populate_param_list_recur(tree.param2, param_list)
        else:
            raise CodeGenError(tree, [ast.Parameter, ast.SequentialParameter])

    def gen_expression(self, tree):
        """ given a general expr and propagate to appropriate expr func """
        if type(tree) is ast.IntegerExpression:
            self.append_code((LOAD_CONST, tree.value))
        elif type(tree) is ast.VnameExpression:
            curr_ident = self.get_from_env(tree.variable.identifier)
            self.append_code((LOAD_FAST, curr_ident))
        elif type(tree) is ast.UnaryExpression:
            if tree.operator == '-':
                return -(self.gen_expression(tree.expression))
            elif tree.operator == '+':
                return self.gen_expression(tree.expression)
            else:
                raise CodeGenError(tree, ['-', '+'])
        elif type(tree) is ast.BinaryExpression:  
            self.gen_expression(tree.expr1)
            self.gen_expression(tree.expr2)

            op = tree.oper
            if op == '+':
                self.append_code((BINARY_ADD, None))
            elif op == '-':
                self.append_code((BINARY_SUBTRACT, None))
            elif op == '*':
                self.append_code((BINARY_MULTIPLY, None))
            elif op == '/':
                self.append_code((BINARY_DIVIDE, None))
            elif op == '>':
                self.append_code((COMPARE_OP, '>'))
            elif op == '<':
                self.append_code((COMPARE_OP, '<'))
            elif op == '=':
                self.append_code((COMPARE_OP, '=='))
            elif op == '\\':
                self.append_code((BINARY_MODULO, 0))
        elif type(tree) is ast.CallCommand:
            self.gen_call_command(tree)
        elif type(tree) is ast.SequentialParameter:
            self.gen_param(tree)
        else:
            raise CodeGenError(tree, ast.Expression)

    def gen_assign_command(self, tree):
        """ given an ast.AssignCommand node, assign expr to ident """
        curr_ident = self.get_from_env(tree.variable.identifier)
        self.gen_expression(tree.expression)
        self.append_code((STORE_FAST, curr_ident))

    def gen_call_command(self, tree):
        """ given an ast.CallCommand node, call function """
        func = tree.identifier
        if func == 'putint':
            self.gen_expression(tree.expression.argname)
            self.append_code((PRINT_ITEM, None))
            self.append_code((PRINT_NEWLINE, None))
        elif func == 'getint': # and type(tree.expression) is ast.VnameExpression:
            self.gen_expression(tree.expression.argname)
            curr_ident = self.get_from_env(tree.expression.argname.variable.identifier)
            self.append_code((LOAD_GLOBAL, 'input'))
            self.append_code((CALL_FUNCTION, 0))
            self.append_code((STORE_FAST, curr_ident))
        else:
            self.append_code((LOAD_FAST, func))
            num_params = self.gen_param(tree.expression)
            self.append_code((CALL_FUNCTION, num_params))

    def gen_param(self, tree):
        """ recursively walk through params to get count """
        num_params = 0
        if type(tree) == ast.Parameter:
            p1 = self.gen_expression(tree.argname)
            num_params = num_params + 1
        elif type(tree) == ast.SequentialParameter:
            tmp_count_1 = self.gen_param(tree.param1)
            tmp_count_2 = self.gen_param(tree.param2)
            num_params = num_params + tmp_count_1 + tmp_count_2
        else:
            raise CodeGenError(tree, [ast.Parameter, ast.SequentialParameter])
    
        return num_params

    def gen_seq_command(self, tree):
        """ given an ast.SequentialCommand node, generate commands """
        self.gen_command(tree.command1)
        self.gen_command(tree.command2)

    def gen_if_command(self, tree):
        """ append appropriate bytecode for ast.IfCommand """
        else_command = Label()
        exit_command = Label()
        # if expression
        self.gen_expression(tree.expression)
        self.append_code((POP_JUMP_IF_FALSE, else_command))
        # then command1
        self.gen_command(tree.command1)
        self.append_code((JUMP_FORWARD, exit_command))
        # else command2
        self.append_code((else_command, None))
        self.gen_command(tree.command2)
        self.append_code((exit_command, None))

    def gen_while_command(self, tree):
        """ append appropriate bytecode for ast.WhileCommand """
        start_while_loop = Label()
        exit_while_loop  = Label()
     
        # top of while loop
        self.append_code((start_while_loop, None))
        # check condition
        self.gen_expression(tree.expression)
        self.append_code((POP_JUMP_IF_FALSE, exit_while_loop))
        # if condition is true, continue to body of while
        self.gen_command(tree.command)
        self.append_code((JUMP_ABSOLUTE, start_while_loop))
        # if condition is false, exit while loop
        self.append_code((exit_while_loop, None))

    def gen_let_command(self, tree):
        """ append appropriate bytecode for ast.LetCommand """
        self.gen_declaration(tree.declaration)
        self.gen_command(tree.command)
        self.clean_up_env()

    def push_stack(self):
        """ push a stack (list) onto self.code """
        self.code.append([])
       
    def pop_stack(self):
        """ pop top of stack from self.code """
        tos = self.code.pop()
        # pprint.pprint(tos)
        return tos

    def append_code(self, bytecode):
        """ add code to current stack """
        index = len(self.code) - 1
        self.code[index].append(bytecode)

    def push_env(self):
        """ push an env (let and func decl pushes an env) """
        self.env.append({})

    def pop_env(self):
        """ when done with env, pop env """
        return self.env.pop()

    def add_to_env(self, ident):
        """ given an ident, modify ident if already exists. 
        return ident added to env
        """
        index = len(self.env) - 1
        curr_env = self.env[index]

        if ident in curr_env:
            # rename ident to identSCOPE_COUNT
            self.scope_count = self.scope_count + 1
            new_ident = ident + str(self.scope_count)
            curr_env[ident].append(new_ident)
            return new_ident
        else:
            curr_env[ident] = [ident]
            return ident

    def get_from_env(self, ident):
        """ self.env = {ident:[ident,ident1,...,identSCOPE_COUNT]}
        given an ident, return the last item is the list it maps to
        """
        index = len(self.env) - 1
        curr_env = self.env[index]
        
        if curr_env.has_key(ident):
            index = len(curr_env[ident]) - 1
            return curr_env[ident][index] 
        else:   
            pass # variable doesn't exist

    def clean_up_env(self):
        """ we know current scope, remove last elems that end w/ curr scope """
        index = len(self.env) - 1
        curr_env = self.env[index]
        
        for item in curr_env:
            curr_scope = curr_env[item]
            last_i = len(curr_scope)-1
            if curr_scope[last_i].endswith(str(self.scope_count)):
                curr_scope.pop()
        self.scope_count = self.scope_count-1


def get_prog_from_file(input_file):
    """ read and return content of file """
    with open(input_file, 'r') as f:
        content = f.read()
    return content

def check_args():
    """ checks to make sure correct num args and file format are provided"""
    if (len(sys.argv) != 2 or not sys.argv[1].endswith(".mt")):
        print "Usage: codegen.py <mini_triangle_source.mt>"
        exit(0)

def write_pyc_file(code, f):
    """ writes a pyc file. format: magic number, timestamp, compiled bytecode """
    pyc_file = os.path.splitext(f)[0] + '.pyc'
    with open(pyc_file, 'wb') as pyc_f:
        magic = int(imp.get_magic().encode('hex'), 16)        
        pyc_f.write(struct.pack(">L", magic))
        pyc_f.write(struct.pack(">L", time.time()))
        marshal.dump(code.func_code, pyc_f)


if __name__ == '__main__':
    check_args()
    f = sys.argv[1]
    prog = get_prog_from_file(f)
    
    scanner_obj = scanner.Scanner(prog)
        
    try:
        tokens = scanner_obj.scan()
    except scanner.ScannerError as e:
        print e
        sys.exit(0)

    parser_obj = parser.Parser(tokens)

    try:
        tree = parser_obj.parse()
    except parser.ParserError as e:
        print e
        sys.exit(0)

    c = CodeGen(tree)
    bytecode = c.generate()
    write_pyc_file(bytecode, f)