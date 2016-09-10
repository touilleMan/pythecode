#! /usr/bin/env python3

import sys
import argparse
import dis
import marshal
import struct
import time
import logging
import operator
import traceback


__version__ = '0.0.1'
DEBUG = False

# REALLY, LOGGING MODULE REALLY ????
logger = logging.getLogger(__file__)
def setup_logging(debug=False):
    global DEBUG
    DEBUG = debug
    loglevel = logging.DEBUG if debug else logging.WARNING
    logger.setLevel(loglevel)
    steam_handler = logging.StreamHandler()
    steam_handler.setLevel(loglevel)
    logger.addHandler(steam_handler)


parser = argparse.ArgumentParser()
parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'))
parser.add_argument('-c', nargs='?')
parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')


def load_pyc(source):
    # pyc file is composed of
    # 1 - A magic number: two CPython version dependant bytes, then "0d0a" (i.e. "\r\n")
    magic = source.read(4)
    assert magic == b'\xee\x0c\x0d\x0a', magic # CPython 3.5 magic number
    # 2 - A timestamp
    moddate = source.read(8)
    moddate = time.asctime(time.localtime(struct.unpack('L', moddate)[0]))
    # 3 - Code serialized with marshal module
    code_obj = marshal.load(source)

    logger.debug("magic: {}\nmoddate: {}\ncode_obj: {}".format(magic, moddate, code_obj))

    return code_obj


def compile_and_run(source, filesource='<string>'):
    code = compile(source, filesource, 'exec')
    interpreter = Interpreter()
    interpreter.exec_bytecode(code)


def repl():
    # REPL loop, only left this by exceptions (SystemExit in normal case)
    print('Pythecode v%s' % __version__)
    interpreter = Interpreter()
    # Create a root frame with no code to store global variables
    frame = interpreter.make_frame(None)
    interpreter.push_frame(frame)
    while True:
        source = input('>>> ')
        if source == 'quit()':
            break
        elif source:
            code = compile(source + '\n', '<stdin>', 'single')
            try:
                ret = interpreter.exec_bytecode(code)
                if ret is not None:
                    print(ret)
            except:
                traceback.print_exc()


def opcode_has_argument(opcode):
    # See cpython/Include/opcode.h:140
    return opcode >= 90


class Frame:
    BASE_GLOBALS = {
        'abs': abs,
        'dict': dict,
        'help': help,
        'min': min,
        'setattr': setattr,

        'all': all,
        'dir': dir,
        'hex': hex,
        'next': next,
        'slice': slice,

        'any': any,
        'divmod': divmod,
        'id': id,
        'object': object,
        'sorted': sorted,

        'ascii': ascii,
        'enumerate': enumerate,
        'input': input,
        'oct': oct,
        'staticmethod': staticmethod,

        'bin': bin,
        'eval': eval,
        'int': int,
        'open': open,
        'str': str,

        'bool': bool,
        'exec': exec,
        'isinstance': isinstance,
        'ord': ord,
        'sum': sum,

        'bytearray': bytearray,
        'filter': filter,
        'issubclass': issubclass,
        'pow': pow,
        'super': super,

        'bytes': bytes,
        'float': float,
        'iter': iter,
        'print': print,
        'tuple': tuple,

        'callable': callable,
        'format': format,
        'len': len,
        'property': property,
        'type': type,

        'chr': chr,
        'frozenset': frozenset,
        'list': list,
        'range': range,
        'vars': vars,

        'classmethod': classmethod,
        'getattr': getattr,
        'locals': locals,
        'repr': repr,
        'zip': zip,

        'compile': compile,
        'globals': globals,
        'map': map,
        'reversed': reversed,
        '__import__': __import__,

        'complex': complex,
        'hasattr': hasattr,
        'max': max,
        'round': round,

        'delattr': delattr,
        'hash': hash,
        'memoryview': memoryview,
        'set': set
    }

    def __init__(self, code_obj, globals=None, locals=None, prev_frame=None):
        self.cptr = 0
        self.code_obj = code_obj
        self.locals = locals
        self.globals = globals or self.BASE_GLOBALS.copy()
        self.prev_frame = prev_frame
        self.return_value = None


class Function:
    def __init__(self, name, code_obj, args_defaults):
        self.name = name
        self.code_obj = code_obj
        self.args_defaults = args_defaults


class Interpreter:

    def __init__(self):
        self._stack = []
        self._frames = []

    def push_stack(self, value):
        self._stack.append(value)

    def pop_stack(self):
        return self._stack.pop()

    def make_frame(self, code_obj, locals=None):
        # First frame is special
        if not self._frames:
            return Frame(code_obj, locals=locals)
        else:
            return Frame(code_obj, locals=locals or {},
                         globals=self.frame.globals, prev_frame=self.frame)

    def push_frame(self, frame):
        self._frames.append(frame)

    def pop_frame(self):
        return self._frames.pop()

    @property
    def frame(self):
        return self._frames[-1]

    def run_frame(self, frame):
        if DEBUG:
            print('==> entering frame')
            dis.dis(frame.code_obj)
        self.push_frame(frame)
        co_code = list(frame.code_obj.co_code)
        why = None
        while not why:
            opcode = co_code[frame.cptr]
            opname = dis.opname[opcode]
            op = getattr(self, opname, None)
            assert op, "Bytecode `%s` not supported" % opname
            msg = 'Stack: %s\n%s =>\t%s' % (self._stack, frame.cptr, opname)
            if opcode_has_argument(opcode):
                # Retrieve argument and update the code pointer
                arg1, arg2 = co_code[frame.cptr+1], co_code[frame.cptr+2]
                logger.debug(msg + '(%s, %s)' % (arg1, arg2))
                why = op(arg1, arg2)
                frame.cptr += 2
            else:
                logger.debug(msg)
                why = op()
            frame.cptr += 1
        frame = self.pop_frame()
        if DEBUG:
            print('<== leaving frame')
            dis.dis(frame.code_obj)
        return frame.return_value

    def exec_bytecode(self, code_obj):
        frame = self.make_frame(code_obj)
        return self.run_frame(frame)

    # Bytecode instructions

    def _locals_lookup(self, name):
        # First search in locals, then in global
        if self.frame.locals and name in self.frame.locals:
            return self.frame.locals[name]
        elif name in self.frame.globals:
            return self.frame.globals[name]
        else:
            raise NameError("name '%s' is not defined" % name)

    def LOAD_NAME(self, arg, _):
        name = self.frame.code_obj.co_names[arg]
        value = self._locals_lookup(name)
        self.push_stack(value)

    def LOAD_GLOBAL(self, arg, _):
        name = self.frame.code_obj.co_names[arg]
        value = self.frame.globals[name]
        self.push_stack(value)

    def LOAD_CONST(self, arg, _):
        value = self.frame.code_obj.co_consts[arg]
        self.push_stack(value)

    def LOAD_FAST(self, arg, _):
        name = self.frame.code_obj.co_varnames[arg]
        value = self._locals_lookup(name)
        self.push_stack(value)

    def STORE_FAST(self, arg, _):
        name = self.frame.code_obj.co_varnames[arg]
        self.frame.locals[name] = self.pop_stack()

    def STORE_NAME(self, arg, _):
        name = self.frame.code_obj.co_names[arg]
        value = self.pop_stack()
        if not self.frame.locals:
            self.frame.globals[name] = value
        else:
            self.frame.locals[name] = value

    def CALL_FUNCTION(self, len_pos, len_kw):
        assert not len_kw, 'Not supported kwargs'
        # right-most parameter on top of the stack
        posargs = list(reversed([self.pop_stack() for _ in range(len_pos)]))
        func = self.pop_stack()
        pre_call_stack_ptr = len(self._stack)
        if isinstance(func, Function):
            # func is a code object
            code = func.code_obj
            locals = {}
            assert not code.co_kwonlyargcount
            len_defaults = len(func.args_defaults)
            no_defaults_count = code.co_argcount - len_defaults
            for i in range(code.co_argcount):
                if i < len(posargs):
                    value = posargs[i]
                else:
                    # args_defaults is a reversed list
                    value = func.args_defaults[i - no_defaults_count]
                locals[code.co_varnames[i]] = value

            frame = self.make_frame(code, locals=locals)
            ret = self.run_frame(frame)
        else:
            # func is a builtin
            ret = func(*posargs)
        assert pre_call_stack_ptr == len(self._stack)  # sanity check
        self.push_stack(ret)

    def POP_TOP(self):
        self.pop_stack()

    def RETURN_VALUE(self):
        self.frame.return_value = self.pop_stack()
        return 'return'

    def MAKE_FUNCTION(self, argc, _):
        func_name = self.pop_stack()
        func_code_obj = self.pop_stack()
        func_args_defaults = list(reversed([self.pop_stack() for _ in range(argc)]))
        func = Function(func_name, func_code_obj, func_args_defaults)
        self.push_stack(func)

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def COMPARE_OP(self, op, _):
        x2 = self.pop_stack()
        x1 = self.pop_stack()
        ret = self.COMPARE_OPERATORS[op](x1, x2)
        self.push_stack(ret)

    def POP_JUMP_IF_FALSE(self, target, _):
        if not self.pop_stack():
            self.frame.cptr = target - 3

    def POP_JUMP_IF_TRUE(self, target, _):
        if self.pop_stack():
            self.frame.cptr = target - 3

    def JUMP_FORWARD(self, delta, _):
        self.frame.cptr += delta

    def _build_binary_op(op):

        def operation(self):
            tos = self.pop_stack()
            tos1 = self.pop_stack()
            self.push_stack(op(tos1, tos))

        return operation

    BINARY_POWER = _build_binary_op(pow)
    BINARY_MULTIPLY = _build_binary_op(operator.mul)
    BINARY_FLOOR_DIVIDE = _build_binary_op(operator.floordiv)
    BINARY_TRUE_DIVIDE = _build_binary_op(operator.truediv)
    BINARY_MODULO = _build_binary_op(operator.mod)
    BINARY_ADD = _build_binary_op(operator.add)
    BINARY_SUBTRACT = _build_binary_op(operator.sub)
    BINARY_SUBSCR = _build_binary_op(operator.getitem)
    BINARY_LSHIFT = _build_binary_op(operator.lshift)
    BINARY_RSHIFT = _build_binary_op(operator.rshift)
    BINARY_AND = _build_binary_op(operator.and_)
    BINARY_XOR = _build_binary_op(operator.xor)
    BINARY_OR = _build_binary_op(operator.or_)

    def PRINT_EXPR(self):
        print(self.pop_stack())

    def BUILD_TUPLE(self, count, _):
        value = tuple(reversed([self.pop_stack() for _ in range(count)]))
        self.push_stack(value)

if __name__ == '__main__':
    args = parser.parse_args()
    interpreter = Interpreter()
    setup_logging(args.debug)
    if args.infile:
        if args.infile.name.endswith('.py'):
            compile_and_run(args.infile.read().decode('utf8'), args.infile.name)
        elif args.infile.name.endswith('.pyc'):
            code_obj = load_pyc(args.infile)
            Interpreter().exec_bytecode(code_obj)
        else:
            raise RuntimeError('infile only accept .py and .pyc files')
    elif args.c:
        compile_and_run(args.c, '<stdin>')
    else:
        repl()
