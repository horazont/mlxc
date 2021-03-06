import asyncio
import contextlib
import os.path
import pathlib
import unittest
import unittest.mock
import xml.sax.handler

import xdg.BaseDirectory

import aioxmpp.errors
import aioxmpp.utils as aioxmpp_utils

from aioxmpp.testutils import (
    run_coroutine,
)

import jclib.utils as utils


class Test_imports_from_aioxmpp(unittest.TestCase):
    def test_imports(self):
        self.assertIs(
            utils.namespaces,
            aioxmpp_utils.namespaces
        )


class Testjabbercat_ns(unittest.TestCase):
    def test_account_namespace(self):
        self.assertEqual(
            "https://xmlns.jabbercat.org/core/account/1.0",
            utils.jabbercat_ns.account
        )

    def test_roster_namespace(self):
        self.assertEqual(
            "https://xmlns.jabbercat.org/core/roster/1.0",
            utils.jabbercat_ns.roster
        )


class Testjclib_uid(unittest.TestCase):
    def test_uid(self):
        self.assertEqual(
            utils.jclib_uid,
            "dns:jabbercat.org"
        )


class Testmultiopen(unittest.TestCase):
    def setUp(self):
        self.paths = [
            "/foo/bar",
            "/baz",
            "/fnord",
        ]

    def test_first_success(self):
        mode = object()
        encoding = object()
        obj = object()

        with contextlib.ExitStack() as stack:
            open_ = stack.enter_context(unittest.mock.patch(
                "builtins.open"
            ))
            open_.return_value = obj

            result = utils.multiopen(
                self.paths,
                "foo.xml",
                mode,
                encoding=encoding)

        self.assertIs(
            result,
            obj)

        self.assertSequenceEqual(
            open_.mock_calls,
            [
                unittest.mock.call(
                    os.path.join(self.paths[0], "foo.xml"),
                    mode,
                    encoding=encoding)
            ]
        )

    def test_tries_and_returns_first_success(self):
        mode = object()
        encoding = object()
        obj = object()

        excs = [FileNotFoundError() for i in range(len(self.paths)-1)]
        excs_to_use = list(excs)
        call_rec = unittest.mock.Mock()

        def open_mock(*args, **kwargs):
            call_rec(*args, **kwargs)
            if excs_to_use:
                raise excs_to_use.pop(0)
            return obj

        with contextlib.ExitStack() as stack:
            open_ = stack.enter_context(unittest.mock.patch(
                "builtins.open",
                open_mock
            ))

            result = utils.multiopen(
                self.paths,
                "foo.xml",
                mode,
                encoding=encoding)

        self.assertSequenceEqual(
            call_rec.mock_calls,
            [
                unittest.mock.call(
                    os.path.join(path, "foo.xml"),
                    mode,
                    encoding=encoding)
                for path in self.paths
            ]
        )


class Testis_write_mode(unittest.TestCase):
    def test_open_r(self):
        self.assertFalse(utils.is_write_mode("r"))
        self.assertFalse(utils.is_write_mode("rb"))
        self.assertFalse(utils.is_write_mode("rt"))

    def test_open_rplus(self):
        self.assertTrue(utils.is_write_mode("r+"))
        self.assertTrue(utils.is_write_mode("r+b"))
        self.assertTrue(utils.is_write_mode("r+t"))

    def test_open_w(self):
        self.assertTrue(utils.is_write_mode("w"))
        self.assertTrue(utils.is_write_mode("wb"))
        self.assertTrue(utils.is_write_mode("wt"))

    def test_open_wplus(self):
        self.assertTrue(utils.is_write_mode("w+"))
        self.assertTrue(utils.is_write_mode("w+b"))
        self.assertTrue(utils.is_write_mode("w+t"))

    def test_open_a(self):
        self.assertTrue(utils.is_write_mode("a"))
        self.assertTrue(utils.is_write_mode("ab"))
        self.assertTrue(utils.is_write_mode("at"))

    def test_open_aplus(self):
        self.assertTrue(utils.is_write_mode("a+"))
        self.assertTrue(utils.is_write_mode("a+b"))
        self.assertTrue(utils.is_write_mode("a+t"))

    def test_open_x(self):
        self.assertTrue(utils.is_write_mode("x"))
        self.assertTrue(utils.is_write_mode("xb"))
        self.assertTrue(utils.is_write_mode("xt"))

    def test_open_xplus(self):
        self.assertTrue(utils.is_write_mode("x+"))
        self.assertTrue(utils.is_write_mode("x+b"))
        self.assertTrue(utils.is_write_mode("x+t"))


class Testxdgopen_generic(unittest.TestCase):
    def test_open_readable(self):
        paths = ["/foo/bar", "/fnord", "/baz"]

        base = unittest.mock.Mock()
        base.load_paths.return_value = iter(paths)
        resource = ["foo", "bar"]
        encoding = object()
        mode = object()

        with contextlib.ExitStack() as stack:
            multiopen = stack.enter_context(
                unittest.mock.patch("jclib.utils.multiopen",
                                    new=base.multiopen)
            )
            is_write_mode = stack.enter_context(
                unittest.mock.patch("jclib.utils.is_write_mode",
                                    new=base.is_write_mode)
            )
            is_write_mode.return_value = False

            utils.xdgopen_generic(
                resource,
                "foo.xml",
                mode,
                load_paths=base.load_paths,
                save_path=base.save_path,
                encoding=encoding
            )

        self.assertSequenceEqual(
            base.mock_calls,
            [
                unittest.mock.call.is_write_mode(mode),
                unittest.mock.call.load_paths(*resource),
                unittest.mock.call.multiopen(
                    list(reversed(paths)),
                    "foo.xml",
                    mode=mode,
                    encoding=encoding
                )
            ]
        )

    def test_open_writable(self):
        path = "/foo/bar"

        base = unittest.mock.Mock()
        base.save_path.return_value = path
        resource = ["foo", "bar"]
        encoding = object()
        mode = object()

        with contextlib.ExitStack() as stack:
            open_ = stack.enter_context(
                unittest.mock.patch("builtins.open",
                                    new=base.open_)
            )
            is_write_mode = stack.enter_context(
                unittest.mock.patch("jclib.utils.is_write_mode",
                                    new=base.is_write_mode)
            )
            is_write_mode.return_value = True

            utils.xdgopen_generic(
                resource,
                "foo.xml",
                mode,
                load_paths=base.load_paths,
                save_path=base.save_path,
                encoding=encoding
            )

        self.assertSequenceEqual(
            base.mock_calls,
            [
                unittest.mock.call.is_write_mode(mode),
                unittest.mock.call.save_path(*resource),
                unittest.mock.call.open_(
                    os.path.join(path, "foo.xml"),
                    mode=mode,
                    encoding=encoding
                )
            ]
        )


class Testxdgdataopen(unittest.TestCase):
    def test_delegate_to_xdgopen_generic(self):
        mode = "fnord"
        encoding = object()
        resource = object()

        with unittest.mock.patch(
                "jclib.utils.xdgopen_generic"
        ) as xdgopen_generic:
            utils.xdgdataopen(resource, "baz.xml",
                              mode=mode,
                              encoding=encoding)

        self.assertSequenceEqual(
            xdgopen_generic.mock_calls,
            [
                unittest.mock.call(
                    resource,
                    "baz.xml",
                    mode,
                    xdg.BaseDirectory.load_data_paths,
                    xdg.BaseDirectory.save_data_path,
                    encoding=encoding
                )
            ]
        )


class Testwrite_xso(unittest.TestCase):
    def test_write_to_io(self):
        base = unittest.mock.Mock()

        instance = base.XMPPXMLGenerator()
        base.mock_calls.clear()

        dest = base.dest
        xso = base.xso

        with unittest.mock.patch(
                "aioxmpp.xml.XMPPXMLGenerator",
                new=base.XMPPXMLGenerator
        ) as XMPPXMLGenerator:
            utils.write_xso(dest, xso)

        self.assertSequenceEqual(
            base.mock_calls,
            [
                unittest.mock.call.XMPPXMLGenerator(
                    out=dest,
                    short_empty_elements=True),
                unittest.mock.call.XMPPXMLGenerator().startDocument(),
                unittest.mock.call.XMPPXMLGenerator().characters("\n"),
                unittest.mock.call.xso.unparse_to_sax(
                    instance
                ),
                unittest.mock.call.XMPPXMLGenerator().characters("\n"),
                unittest.mock.call.XMPPXMLGenerator().endDocument()
            ]
        )


class Testread_xso(unittest.TestCase):
    def test_read_from_io(self):
        base = unittest.mock.Mock()

        xso_parser = base.XSOParser()
        sax_driver = base.SAXDriver()

        base.mock_calls.clear()

        with contextlib.ExitStack() as stack:
            XSOParser = stack.enter_context(unittest.mock.patch(
                "aioxmpp.xso.XSOParser",
                base.XSOParser
            ))
            SAXDriver = stack.enter_context(unittest.mock.patch(
                "aioxmpp.xso.SAXDriver",
                base.SAXDriver
            ))
            make_parser = stack.enter_context(unittest.mock.patch(
                "xml.sax.make_parser",
                base.make_parser
            ))

            utils.read_xso(base.src, {
                base.A: base.cb,
            })

        self.assertSequenceEqual(
            base.mock_calls,
            [
                unittest.mock.call.XSOParser(),
                unittest.mock.call.XSOParser().add_class(
                    base.A,
                    base.cb
                ),
                unittest.mock.call.SAXDriver(xso_parser),
                unittest.mock.call.make_parser(),
                unittest.mock.call.make_parser().setFeature(
                    xml.sax.handler.feature_namespaces,
                    True),
                unittest.mock.call.make_parser().setFeature(
                    xml.sax.handler.feature_external_ges,
                    False),
                unittest.mock.call.make_parser().setContentHandler(
                    sax_driver),
                unittest.mock.call.make_parser().parse(base.src)
            ]
        )


class Testlogged_async(unittest.TestCase):
    def test_attaches_log_function(self):
        base = unittest.mock.Mock()

        loop = object()
        coro = object()
        name = object()
        with contextlib.ExitStack() as stack:
            async = stack.enter_context(unittest.mock.patch(
                "asyncio.async",
                new=base.async
            ))

            partial = stack.enter_context(unittest.mock.patch(
                "functools.partial",
                new=base.partial
            ))

            task = utils.logged_async(coro, loop=loop, name=name)

        calls = list(base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.async(coro, loop=loop),
                unittest.mock.call.partial(
                    utils._logged_task_done,
                    name=name),
                unittest.mock.call.async().add_done_callback(
                    partial()
                ),
            ]
        )

        self.assertEqual(
            task,
            async()
        )

    def test_uses_current_event_loop_as_default(self):
        base = unittest.mock.Mock()

        coro = object()
        with contextlib.ExitStack() as stack:
            async = stack.enter_context(unittest.mock.patch(
                "asyncio.async",
                new=base.async
            ))

            partial = stack.enter_context(unittest.mock.patch(
                "functools.partial",
                new=base.partial
            ))

            get_event_loop = stack.enter_context(unittest.mock.patch(
                "asyncio.get_event_loop",
                new=base.get_event_loop
            ))

            task = utils.logged_async(coro)

        calls = list(base.mock_calls)
        self.assertSequenceEqual(
            calls,
            [
                unittest.mock.call.get_event_loop(),
                unittest.mock.call.async(coro, loop=get_event_loop()),
                unittest.mock.call.partial(
                    utils._logged_task_done,
                    name=async(),
                ),
                unittest.mock.call.async().add_done_callback(
                    partial()
                ),
            ]
        )

        self.assertEqual(
            task,
            async()
        )

    def test_logged_task_done_no_exception(self):
        name = object()

        task = unittest.mock.Mock()

        with unittest.mock.patch("jclib.utils.logger") as logger:
            utils._logged_task_done(task, name=name)

        self.assertSequenceEqual(
            logger.mock_calls,
            [
                unittest.mock.call.info("task %s returned a value: %r",
                                        name, task.result())
            ]
        )

    def test_logged_task_done_cancelled(self):
        name = object()

        task = unittest.mock.Mock()
        task.result.side_effect = asyncio.CancelledError()

        with unittest.mock.patch("jclib.utils.logger") as logger:
            utils._logged_task_done(task, name=name)

        self.assertSequenceEqual(
            logger.mock_calls,
            [
                unittest.mock.call.debug("task %s cancelled",
                                         name)
            ]
        )

    def test_logged_task_done_exception(self):
        name = object()

        task = unittest.mock.Mock()
        task.result.side_effect = Exception()

        with unittest.mock.patch("jclib.utils.logger") as logger:
            utils._logged_task_done(task, name=name)

        self.assertSequenceEqual(
            logger.mock_calls,
            [
                unittest.mock.call.exception("task %s failed",
                                             name)
            ]
        )


class Testmkdir_exist_ok(unittest.TestCase):
    def test_successful_mkdir(self):
        p = unittest.mock.Mock()
        utils.mkdir_exist_ok(p)
        self.assertSequenceEqual(
            p.mock_calls,
            [
                unittest.mock.call.mkdir(parents=True),
            ]
        )

    def test_mkdir_exists_but_is_directory(self):
        p = unittest.mock.Mock()
        p.is_dir.return_value = True
        p.mkdir.side_effect = FileExistsError()
        utils.mkdir_exist_ok(p)
        self.assertSequenceEqual(
            p.mock_calls,
            [
                unittest.mock.call.mkdir(parents=True),
                unittest.mock.call.is_dir()
            ]
        )

    def test_mkdir_exists_but_is_not_directory(self):
        p = unittest.mock.Mock()
        p.is_dir.return_value = False
        exc = FileExistsError()
        p.mkdir.side_effect = exc
        with self.assertRaises(FileExistsError) as ctx:
            utils.mkdir_exist_ok(p)

        self.assertIs(ctx.exception, exc)

        self.assertSequenceEqual(
            p.mock_calls,
            [
                unittest.mock.call.mkdir(parents=True),
                unittest.mock.call.is_dir()
            ]
        )


class Testfsync_dir(unittest.TestCase):
    def setUp(self):
        self.base = unittest.mock.Mock()
        self.os_open = self.base.os_open
        self.os_fsync = self.base.os_fsync
        self.os_close = self.base.os_close
        self.path = unittest.mock.Mock(spec=pathlib.Path)

        self.patches = [
            unittest.mock.patch("os.open", new=self.os_open),
            unittest.mock.patch("os.fsync", new=self.os_fsync),
            unittest.mock.patch("os.close", new=self.os_close),
        ]

        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def test_open_fsync_close(self):
        utils.fsync_dir(self.path)

        self.assertSequenceEqual(
            list(self.base.mock_calls),
            [
                unittest.mock.call.os_open(
                    str(self.path),
                    os.O_DIRECTORY | os.O_RDONLY,
                ),
                unittest.mock.call.os_fsync(self.os_open()),
                unittest.mock.call.os_close(self.os_open())
            ]
        )

    def test_closes_on_fsync_exception(self):
        class FooException(Exception):
            pass

        self.os_fsync.side_effect = FooException()

        with self.assertRaises(FooException):
            utils.fsync_dir(self.path)

        self.os_close.assert_called_once_with(self.os_open())


class Testsafe_writer(unittest.TestCase):
    def setUp(self):
        self.patchers = [
            unittest.mock.patch("pathlib.Path"),
            unittest.mock.patch("tempfile.NamedTemporaryFile"),
            unittest.mock.patch("os.replace"),
            unittest.mock.patch("os.unlink"),
            unittest.mock.patch("os.fsync"),
        ]
        self.tmpfile = unittest.mock.Mock()
        self.path = unittest.mock.Mock()
        self.pathlib_Path = self.patchers[0].start()
        self.pathlib_Path.return_value = self.path
        self.tempfile_NamedTemporaryFile = self.patchers[1].start()
        self.tempfile_NamedTemporaryFile().__enter__.return_value = self.tmpfile
        self.tempfile_NamedTemporaryFile.reset_mock()
        self.os_replace = self.patchers[2].start()
        self.os_unlink = self.patchers[3].start()
        self.os_fsync = self.patchers[4].start()

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()

    def test_provides_tempfile_in_cm(self):
        cm = utils.safe_writer(
            unittest.mock.sentinel.path,
            mode=unittest.mock.sentinel.mode)
        f = cm.__enter__()
        self.pathlib_Path.assert_called_once_with(
            unittest.mock.sentinel.path
        )
        self.tempfile_NamedTemporaryFile.assert_called_once_with(
            mode=unittest.mock.sentinel.mode,
            dir=str(self.path.parent),
            delete=False,
        )
        self.tempfile_NamedTemporaryFile().__enter__.assert_called_once_with()
        self.assertEqual(
            f,
            self.tempfile_NamedTemporaryFile().__enter__(),
        )

        self.os_replace.assert_not_called()
        self.os_unlink.assert_not_called()

    def test_unlinks_tempfile_on_exception(self):
        class FooException(Exception):
            pass

        with contextlib.ExitStack() as stack:
            stack.enter_context(self.assertRaises(FooException))
            cm = utils.safe_writer(
                unittest.mock.sentinel.path,
                mode=unittest.mock.sentinel.mode)
            stack.enter_context(cm)
            raise FooException()

        self.os_unlink.assert_called_once_with(
            self.tempfile_NamedTemporaryFile().__enter__().name
        )

    def test_replace_dest_on_success(self):
        with contextlib.ExitStack() as stack:
            cm = utils.safe_writer(
                unittest.mock.sentinel.path,
                mode=unittest.mock.sentinel.mode)
            stack.enter_context(cm)

        self.os_replace.assert_called_once_with(
            self.tempfile_NamedTemporaryFile().__enter__().name,
            str(self.path),
        )

    def test_correct_flush_and_sync_on_success(self):
        self.common = unittest.mock.Mock()

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                unittest.mock.patch("os.fsync", new=self.common.fsync),
            )
            stack.enter_context(
                unittest.mock.patch("os.replace", new=self.common.replace),
            )
            stack.enter_context(
                unittest.mock.patch.object(self.tmpfile, "flush",
                                           new=self.common.flush),
            )

            cm = utils.safe_writer(
                unittest.mock.sentinel.path,
                mode=unittest.mock.sentinel.mode)
            stack.enter_context(cm)

        self.assertSequenceEqual(
            self.common.mock_calls,
            [
                unittest.mock.call.flush(),
                unittest.mock.call.fsync(self.tmpfile.fileno()),
                unittest.mock.call.replace(unittest.mock.ANY,
                                           unittest.mock.ANY)
            ]
        )

    def test_extra_paranoia_flush(self):
        self.common = unittest.mock.Mock()

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                unittest.mock.patch("os.fsync", new=self.common.fsync),
            )
            stack.enter_context(
                unittest.mock.patch("os.replace", new=self.common.replace),
            )
            stack.enter_context(
                unittest.mock.patch("os.open", new=self.common.open),
            )
            stack.enter_context(
                unittest.mock.patch.object(self.tmpfile, "flush",
                                           new=self.common.flush),
            )
            stack.enter_context(
                unittest.mock.patch("jclib.utils.fsync_dir",
                                    new=self.common.fsync_dir)
            )

            cm = utils.safe_writer(
                unittest.mock.sentinel.path,
                mode=unittest.mock.sentinel.mode,
                extra_paranoia=True)
            stack.enter_context(cm)

        self.assertSequenceEqual(
            self.common.mock_calls,
            [
                unittest.mock.call.flush(),
                unittest.mock.call.fsync(self.tmpfile.fileno()),
                unittest.mock.call.replace(unittest.mock.ANY,
                                           unittest.mock.ANY),
                unittest.mock.call.fsync_dir(self.path.parent),
            ]
        )


class TestDelayedInvocation(unittest.TestCase):
    def setUp(self):
        self.sink = unittest.mock.Mock()
        self.loop = asyncio.get_event_loop()
        self.delay = 0.05
        self.dac = utils.DelayedInvocation(
            self.sink,
            self.delay,
            loop=self.loop,
        )

    def test_calls_sink_delayedly_with_arguments_in_list(self):
        self.dac("arg1", "arg2", kwarg="foo")
        self.sink.assert_not_called()

        run_coroutine(asyncio.sleep(self.delay/2))

        self.sink.assert_not_called()

        run_coroutine(asyncio.sleep(self.delay/2 + self.delay/10))

        self.sink.assert_called_once_with(
            [(("arg1", "arg2",), {"kwarg": "foo"})]
        )

    def test_schedules_call_via_loop(self):
        with unittest.mock.patch.object(self.loop, "call_later") as call_later:
            self.dac("arg1", "arg2", kwarg="foo")

        call_later.assert_called_once_with(
            self.delay,
            unittest.mock.ANY,
        )

    def test_multiple_calls_within_delay_delay_call_further(self):
        self.dac("arg1")
        run_coroutine(asyncio.sleep(self.delay/2 + self.delay/10))

        self.dac("arg2")
        run_coroutine(asyncio.sleep(self.delay/2))

        self.sink.assert_not_called()

        run_coroutine(asyncio.sleep(self.delay/2 + self.delay/10))

        self.sink.assert_called_once_with(
            [
                (("arg1",), {}),
                (("arg2",), {}),
            ]
        )

    def test_delay_change_takes_effect_on_next_call(self):
        self.dac("arg1")
        run_coroutine(asyncio.sleep(self.delay/2 + self.delay/10))

        self.sink.assert_not_called()

        self.dac.delay = self.delay/2
        self.dac("arg2")
        run_coroutine(asyncio.sleep(self.delay/2 + self.delay/10))
        self.sink.assert_called_once()

    def test_max_delay_default(self):
        self.assertIsNone(self.dac.max_delay)

    def test_max_delay_is_settable(self):
        self.dac.max_delay = 0.1
        self.assertEqual(self.dac.max_delay, 0.1)

    def test_max_delay_limits_scheduling_of_multiple_calls(self):
        self.dac.max_delay = self.delay * 1.2

        self.dac("arg1")
        run_coroutine(asyncio.sleep(self.delay/2))

        self.dac("arg2")
        run_coroutine(asyncio.sleep(self.delay/2))
        self.sink.assert_not_called()

        run_coroutine(asyncio.sleep(self.delay*2/10))
        self.sink.assert_called_once()

    def test_max_delay_limits_scheduling_of_several_calls(self):
        self.dac.max_delay = self.delay * 2

        for i in range(7):
            self.dac("arg{}".format(i))
            run_coroutine(asyncio.sleep(self.delay/4 - self.delay/70))
            self.sink.assert_not_called()

        run_coroutine(asyncio.sleep(self.delay/4 + self.delay/10))
        self.sink.assert_called_once_with(
            [
                (("arg{}".format(i),), {})
                for i in range(7)
            ]
        )

    def test_arguments_are_purged_on_invocation(self):
        self.dac("arg1")
        run_coroutine(asyncio.sleep(self.delay*1.1))

        self.sink.assert_called_once_with(
            [(("arg1",), {})]
        )
        self.sink.reset_mock()

        self.dac("arg2")
        run_coroutine(asyncio.sleep(self.delay*1.1))

        self.sink.assert_called_once_with(
            [(("arg2",), {})]
        )

    def test_max_delay_can_be_passed_via_constructor(self):
        dac = utils.DelayedInvocation(
            self.sink,
            self.delay,
            max_delay=0.6,
        )
        self.assertEqual(dac.max_delay, 0.6)

    def test_max_delay_can_be_set_to_None(self):
        self.dac.max_delay = 0.1
        self.dac.max_delay = None

    def test_reject_max_delay_less_than_zero(self):
        with self.assertRaisesRegex(
                ValueError,
                "must not be negative"):
            self.dac.max_delay = -0.1

    def test_reject_max_delay_less_than_zero_in_constructor(self):
        with self.assertRaisesRegex(
                ValueError,
                "max_delay must not be negative"):
            utils.DelayedInvocation(
                self.sink,
                self.delay,
                max_delay=-0.1
            )

    def test_delay_can_not_be_set_to_None(self):
        self.dac.delay = 0.1

        with self.assertRaisesRegex(
                ValueError,
                "must not be None"):
            self.dac.delay = None

    def test_reject_None_delay_in_constructor(self):
        with self.assertRaisesRegex(
                ValueError,
                "delay must not be None"):
            utils.DelayedInvocation(
                self.sink,
                None,
            )

    def test_reject_delay_less_than_zero(self):
        with self.assertRaisesRegex(
                ValueError,
                "must not be negative"):
            self.dac.delay = -0.1

    def test_reject_delay_less_than_zero_in_constructor(self):
        with self.assertRaisesRegex(
                ValueError,
                "delay must not be negative"):
            utils.DelayedInvocation(
                self.sink,
                -0.1,
            )
