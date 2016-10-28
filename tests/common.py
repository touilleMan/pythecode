import pytest
import inspect

from pythecode import Interpreter, Cell, setup_logging


@pytest.fixture
def interpreter():
    interpreter = Interpreter()

    def test_run_as_module(func):
        # Retrive function's source code and recompile it as a
        # standalone module
        source = inspect.getsource(func).split('\n')
        # First line of code is the function signature, we can skip it
        start_indent = 0
        for c in source[1]:
            if c == ' ':
                start_indent += 1
            else:
                break
        body = []
        for raw_line in source[1:]:
            if len(raw_line) < start_indent:
                body.append('')
            else:
                body.append(raw_line[start_indent:])
        code = compile('\n'.join(body),
                       'Recompiled `%s.%s`' % (func.__module__, func.__name__),
                       'exec')
        interpreter.exec_bytecode(code)

    def test_run_as_function(func, *args):
        code = func.__code__
        assert code.co_argcount == len(args)
        locals = {code.co_varnames[i]: arg for i, arg in enumerate(args)}
        root_frame = interpreter.make_frame(compile('', '', 'exec'))
        root_frame.cells[func.__name__] = Cell(func)
        interpreter.push_frame(root_frame)
        return interpreter.exec_bytecode(func.__code__, locals=locals)

    interpreter.test_run_as_function = test_run_as_function
    interpreter.test_run_as_module = test_run_as_module
    if pytest.config.getoption('debuglogs'):
        setup_logging(debug=True)
    return interpreter
