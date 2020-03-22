# -*- coding: utf-8 -*-
from __future__ import annotations

# -- stdlib --
# -- third party --
import gevent

# -- own --
from ..mock import Environ, EventTap
from utils.misc import BatchList
from .common import UserInputFuzzingHandler, let_it_go


# -- code --
class GameEnded(Exception):
    pass


def wait():
    gevent.idle(-100)
    gevent.sleep(0.01)
    gevent.idle(-100)


class TestFuzzTHBattleFaith(object):
    def testFuzzTHBattleFaith(self):
        env = Environ()
        t = EventTap()

        me = gevent.getcurrent()

        def fail_crash(g):
            e = Exception('GAME CRASH')
            e.__cause__ = g.runner.exception
            gevent.kill(me, e)
            return g

        s = env.server_core()
        cl = BatchList([env.client_core() for _ in range(6)])
        t.tap(s, *cl)

        c1r = BatchList(cl[1:])
        c = cl[0]
        names = (
            'Reimu', 'Marisa', 'Youmu', 'Sakuya',
            'Satori', 'Koishi', 'Remilia', 'Flandre',
        )
        for i, name in zip(cl, names):
            i.auth.login(name)
        wait()
        assert all(cl.auth.uid)
        c.room.create('Test1', 'THBattleFaith', {})
        wait()
        gid = c.game.gid_of(t[c.events.game_joined])
        c1r.room.join(gid)
        wait()
        assert [gid] * 6 == [i.game.gid_of(t[i.events.game_joined]) for i in cl]

        s.events.game_crashed += fail_crash
        for i in cl:
            g = t[i.events.game_joined]
            i.events.game_crashed += fail_crash
            g.event_observer = UserInputFuzzingHandler(g)

        cl.room.get_ready()
        wait()
        assert [gid] * 6 == [i.game.gid_of(t[i.events.game_started]) for i in cl]

        wait()

        def game_ended(g):
            gevent.kill(me, GameEnded())
            return g

        s.events.game_ended += game_ended

        [i.game.start_game(t[i.events.game_started]) for i in cl]

        try:
            let_it_go(*cl)
        except GameEnded:
            pass
