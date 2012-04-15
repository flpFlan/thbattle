# -*- coding: utf-8 -*-

from ..actions import *
from . import basic
from . import base

class SpellCardAction(UserAction): pass
class InstantSpellCardAction(SpellCardAction): pass

class Demolition(InstantSpellCardAction):
    # 城管执法

    def apply_action(self):
        g = Game.getgame()
        source = self.source
        target = self.target

        #cards = random_choose_card(target, target.cards, 1)
        categories = [
            target.cards,
            target.showncards,
            target.equips,
            target.fatetell,
        ]
        card = choose_peer_card(source, target, categories)
        if not card:
            card = random_choose_card(categories)
            if not card:
                return False

        self.card = card
        g.players.exclude(target).reveal(card)
        g.process_action(
            DropCards(target=target, cards=[card])
        )
        return True

class Reject(InstantSpellCardAction):
    # 好人卡
    def __init__(self, source, target_act):
        self.source = source
        self.target_act = target_act
        self.target = target_act.source

    def apply_action(self):
        if not isinstance(self.target_act, InstantSpellCardAction):
            return False
        self.target_act.cancelled = True
        return True

@register_eh
class RejectHandler(EventHandler):
    def handle(self, evt_type, act):
        if evt_type == 'action_before' and isinstance(act, InstantSpellCardAction):
            if act.cancelled: return act # some other thing have done the job

            g = Game.getgame()

            p, input = g.players.user_input_any(
                'choose_card_and_player', self._expects, (self, [])
            )

            if p:
                sid_list, cid_list = input
                cards = g.deck.lookupcards(cid_list) # card was already revealed

                if sid_list: # skill selected
                    cards = skill_wrap(actor, sid_list, cards)

                card = cards[0]

                action = Reject(source=p, target_act=act)
                action.associated_card = card
                g.process_action(DropUsedCard(p, [card]))
                g.process_action(action)
        return act

    def _expects(self, p, input):
        from utils import check, CheckFailed
        try:
            check_type([[int, Ellipsis], [int, Ellipsis]], input)

            sid_list, cid_list = input

            g = Game.getgame()
            cards = g.deck.lookupcards(cid_list)
            check(cards)
            card = cards[0]
            check(card in p.cards)

            g.players.exclude(p).reveal(card)

            check(self.cond([card]))
            return True
        except CheckFailed as e:
            return False

    def cond(self, cardlist):
        from utils import check, CheckFailed
        from .. import cards
        try:
            check(len(cardlist) == 1)
            check(cardlist[0].is_card(cards.RejectCard))
            return True
        except CheckFailed:
            return False

class DelayedSpellCardAction(SpellCardAction): pass # 延时SC

# TODO: code like this only allow ONE such behavior change.

class DelayedLaunchCard(LaunchCard):
    def is_valid(self):
        if not self.card: return False
        if not len(self.target_list) == 1: return False
        return True

    def apply_action(self):
        g = Game.getgame()
        card = self.card
        action = card.associated_action
        assert issubclass(action, DelayedSpellCardAction)

        t = self.target_list[0]
        migrate_cards([card], t.fatetell)
        from .base import VirtualCard
        if card.is_card(VirtualCard):
            migrate_cards(card.associated_cards, t.special)
        return True

@register_eh
class DelayedSpellCardActionHandler(EventHandler):
    def handle(self, evt_type, act):
        if evt_type == 'action_before' and isinstance(act, LaunchCard):
            card = act.card
            aa = card.associated_action
            if issubclass(aa, DelayedSpellCardAction):
                act.__class__ = DelayedLaunchCard

        return act

class SealingArray(DelayedSpellCardAction):
    # 封魔阵
    def apply_action(self):
        g = Game.getgame()
        target = self.target
        from ..cards import Card
        ft = Fatetell(target, lambda card: card.suit != Card.HEART)
        g.process_action(ft)
        if ft.succeeded:
            target.tags['sealed'] = True
        return True

    def fatetell_postprocess(self):
        g = Game.getgame()
        target = self.target
        g.process_action(DropCards(target, [self.associated_card]))

@register_eh
class SealingArrayHandler(EventHandler):
    def handle(self, evt_type, act):
        if evt_type == 'action_before' and isinstance(act, ActionStage):
            actor = act.actor
            if actor.tags.get('sealed'):
                del actor.tags['sealed']
                act.cancelled = True
        return act

class NazrinRod(InstantSpellCardAction):
    # 纳兹琳的探宝棒

    def apply_action(self):
        g = Game.getgame()
        g.process_action(DrawCards(self.target, amount=2))
        return True

class Worshiper(DelayedSpellCardAction):
    # 罪袋
    def apply_action(self):
        g = Game.getgame()
        target = self.target
        from ..cards import Card
        ft = Fatetell(target, lambda card: card.suit == Card.SPADE and 1 <= card.number <= 8)
        g.process_action(ft)
        if ft.succeeded:
            dmg = Damage(None, target, amount=3)
            dmg.associated_action = self
            g.process_action(dmg)
            return True
        return False

    def fatetell_postprocess(self):
        g = Game.getgame()
        target = self.target
        if not self.cancelled and self.succeeded:
            g.process_action(DropCards(target, [self.associated_card]))
        else:
            pl = g.players
            next = pl[pl.index(target) - len(pl) + 1]
            migrate_cards([self.associated_card], next.fatetell)

class YukariDimension(InstantSpellCardAction):
    # 紫的隙间

    def apply_action(self):
        g = Game.getgame()
        source = self.source
        target = self.target

        categories = [
            target.cards,
            target.showncards,
            target.equips,
            target.fatetell,
        ]
        card = choose_peer_card(source, target, categories)
        if not card:
            card = random_choose_card(categories)
            if not card:
                return False

        self.card = card
        source.reveal(card)
        migrate_cards([card], source.cards)
        return True

class BaseDuel(UserAction):
    # 弹幕战
    def apply_action(self):
        g = Game.getgame()
        source = self.source
        target = self.target

        d = (source, target)
        while True:
            d = (d[1], d[0])
            if not g.process_action(basic.UseAttack(d[0])): break

        dmg = Damage(d[1], d[0], amount=1)
        dmg.associated_action = self
        g.process_action(dmg)
        return d[1] is source

class Duel(BaseDuel, InstantSpellCardAction):
    pass

class MapCannonEffect(InstantSpellCardAction):
    # 地图炮
    def apply_action(self):
        g = Game.getgame()
        source, target = self.source, self.target
        graze_action = basic.UseGraze(target)
        if not g.process_action(graze_action):
            dmg = Damage(source, target, amount=1)
            dmg.associated_action = self
            g.process_action(dmg)
            return True
        else:
            return False

class MapCannon(ForEach):
    action_cls = MapCannonEffect

class WorshipersCarnivalEffect(InstantSpellCardAction):
    # 罪袋狂欢
    def apply_action(self):
        g = Game.getgame()
        source, target = self.source, self.target
        use_action = basic.UseAttack(target)
        if not g.process_action(use_action):
            dmg = Damage(source, target, amount=1)
            dmg.associated_action = self
            g.process_action(dmg)
            return True
        else:
            return False

class WorshipersCarnival(ForEach):
    action_cls = WorshipersCarnivalEffect

class FeastEffect(InstantSpellCardAction):
    # 宴会
    def apply_action(self):
        src, tgt = self.source, self.target
        g = Game.getgame()
        if tgt.life < tgt.maxlife:
            g.process_action(basic.Heal(src, tgt))
        else:
            g.process_action(basic.Wine(src, tgt))
        return True

class Feast(ForEach):
    action_cls = FeastEffect

class HarvestEffect(InstantSpellCardAction):
    # 五谷丰登 效果
    def apply_action(self):
        cards = self.parent_action.cards
        cards_avail = [c for c in cards if not c.resides_in.owner]
        cmap = {c.syncid:c for c in cards_avail}
        g = Game.getgame()
        tgt = self.target
        cid = tgt.user_input('harvest_choose', cards_avail)
        card = cmap.get(cid)
        if not card:
            card = random_choose_card([cards_avail])
        migrate_cards([card], tgt.cards)
        g.emit_event('harvest_choose', card)
        return True

class Harvest(ForEach):
    action_cls = HarvestEffect
    def prepare(self):
        tl = self.target_list
        g = Game.getgame()
        cards = g.deck.getcards(len(tl))
        g.players.reveal(cards)
        g.emit_event('harvest_cards', cards)
        self.cards = cards

    def cleanup(self):
        g = Game.getgame()
        g.emit_event('harvest_finish', self)
        dropped = g.deck.droppedcards
        deckcard = g.deck.cards
        migrate_cards([c for c in self.cards if not c.resides_in.owner], dropped)

class Camera(InstantSpellCardAction):
    # 文文的相机
    def apply_action(self):
        src = self.source
        tgt = self.target

        cards = list(tgt.cards)[:2]
        g = Game.getgame()
        g.players.exclude(tgt).reveal(cards)
        migrate_cards(cards, tgt.showncards)

        return True

class DollControl(InstantSpellCardAction):
    def apply_action(self):
        tl = self.target_list
        assert len(tl) == 2
        src = self.source

        controllee, attackee = tl
        cats = [
            controllee.cards,
            controllee.showncards,
        ]
        cards = user_choose_cards(self, controllee, cats)
        g = Game.getgame()

        if cards:
            g.players.reveal(cards)
            g.process_action(LaunchCard(controllee, [attackee], cards[0]))
        else:
            l = [e for e in controllee.equips if e.equipment_category == 'weapon']
            migrate_cards(l, src.cards)
        return True

    def cond(self, cl):
        from .definition import AttackCard
        return cl and cl[0].is_card(AttackCard)

class DonationBox(InstantSpellCardAction):
    def apply_action(self):
        tl = self.target_list
        src = self.source
        assert 0 < len(tl) <= 2
        g = Game.getgame()
        for t in tl:
            cats = [
                t.cards,
                t.showncards,
                t.equips,
            ]
            cards = user_choose_cards(self, t, cats)
            if not cards:
                cards = [random_choose_card(cats)]

            if cards:
                src.reveal(cards)
                migrate_cards(cards, src.cards)

        return True

    def cond(self, cards):
        return len(cards) == 1