import pytest

from .common import interpreter


def _assert_exc(candidate, expected):
    assert candidate.__class__ == expected.__class__
    assert candidate.args == expected.args


def test_exception(interpreter):

    def simple_raise():
        raise Exception('my msg')

    with pytest.raises(Exception) as exc:
        interpreter.test_run_as_function(simple_raise)
    _assert_exc(exc.value, Exception('my msg'))


def test_assert(interpreter):

    # def no_argument():
    #     assert 1 == 2

    # with pytest.raises(AssertionError) as exc:
    #     interpreter.test_run_as_module(no_argument)
    # _assert_exc(exc.value, AssertionError)

    def with_argument():
        assert 1 == 2, 'one is not two'
    with pytest.raises(AssertionError) as exc:
        interpreter.test_run_as_module(with_argument)
    _assert_exc(exc.value, AssertionError('one is not two'))
