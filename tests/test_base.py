import pytest

from .common import interpreter


def test_global_var(interpreter):
    def test():
        intro = 'Introducing: '
        def introduce(a):
            return intro + str(a)

        assert introduce('John') == 'Introducing: John', introduce('John')

    interpreter.test_run_as_module(test)


def test_deref(interpreter):
    def test():
        def deref(a):
            intro = 'Introducing: '
            def introduce(a):
                return intro + str(a)
            ret = introduce(a)
            intro = 'Ladies and gentlemen, '
            ret = introduce(ret)
            return ret

        assert deref('John') == 'Ladies and gentlemen, Introducing: John', deref('John')

    interpreter.test_run_as_module(test)


@pytest.mark.xfail
def test_closure(interpreter):
    def test():
        def with_wrap(func):
            def wrapper(a):
                return 'Wrapped ' + func(a)
            return wrapper

        def hello(a):
            return 'Hello ' + str(a)

        # base = hello('John')
        wrapped = with_wrap(hello)('John')
        # double_wrapped = with_wrap(with_wrap(hello))('John')
        # assert base == 'Hello John', base
        # assert wrapped == 'Wrapped Hello John', wrapped
        # assert double_wrapped == 'Wrapped Wrapped Hello John', double_wrapped

    interpreter.test_run_as_module(test)


def test_module(interpreter):
    def test():
        def fibo(a):
            if a in (0, 1):
                ret = a
            else:
                ret = fibo(a-1) + fibo(a-2)
            return ret
        assert fibo(0) == 0
        assert fibo(3) == 2
        assert fibo(10) == 55

    interpreter.test_run_as_module(test)


def test_base(interpreter):

    def test1():
        assert 2 + 2 == 4
    interpreter.test_run_as_module(test1)

    def test2():
        assert 2 + 2 == 5
    with pytest.raises(AssertionError):
        interpreter.test_run_as_module(test2)


def test_fibo(interpreter):

    def fibo(a):
        if a in (0, 1):
            ret = a
        else:
            ret = fibo(a-1) + fibo(a-2)
        return ret

    assert interpreter.test_run_as_function(fibo, 0) == 0
    assert interpreter.test_run_as_function(fibo, 3) == 2
    assert interpreter.test_run_as_function(fibo, 10) == 55
