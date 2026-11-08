// =============================================================================
//  XY Quick Hack - Self-Erase & Hack Diffusion
//  Target game version 2.50 / redscript
// =============================================================================
//  NO POLLING ANYWHERE.
//
//  Self-Erase uses the same pattern every shipping custom quickhack mod uses
//  (documented in TeleportTakedown's MAKING_CUSTOM_QUICKHACKS.md): the hack
//  applies a tagged status effect, and redscript reacts to the engine's own
//  status effect events.
//
//      NPCPuppet.OnStatusEffectApplied   -> suppress this puppet's perception,
//                                           once
//      NPCPuppet.OnStatusEffectRemoved   -> restore it, once
//
//  The duration (60/120/180 s) is owned by the status effect record itself, so
//  there is no timer in script and nothing re-evaluates every frame. Re-setting
//  the detection overwrite on a timer made the NPC's awareness bar flicker red
//  and reset every 0.5 s - that is what this rewrite removes.
//
//  The tags do the rest, natively:
//      Stealth       -> NPC\NPCPuppet.script:1747 skips the whole
//                       NonStealthQuickHackVictimEvent chain, so the target
//                       never turns hostile
//      ClearThreats  -> :1550 calls TargetTrackerComponent.ClearThreats()
//
//  The Blind tag is deliberately NOT used: it switches the NPC to the
//  Senses.Blind preset (detectionFactor 0.01), which makes them wander around
//  blind. Detection suppression is done with SenseComponent instead, so the
//  target keeps behaving normally.
// =============================================================================

module VH

// =============================================================================
//  Constants
// =============================================================================

public class VH_Defs extends IScriptable {

  public final static func SelfEraseTag() -> CName {
    return n"VH_SelfErase";
  }

  public final static func SpreadRadius() -> Float {
    return 20.0;
  }

  public final static func SpreadMaxTargets() -> Int32 {
    return 99;
  }
}

// =============================================================================
//  Player side bookkeeping (no timers)
// =============================================================================

@addField(PlayerPuppet)
public let vhSelfEraseActive: Bool;

@addField(PlayerPuppet)
private let vhSelfEraseCount: Int32;

@addMethod(PlayerPuppet)
public func VH_NoteSelfErase(delta: Int32) -> Void {
  this.vhSelfEraseCount += delta;

  if this.vhSelfEraseCount < 0 {
    this.vhSelfEraseCount = 0;
  };

  this.vhSelfEraseActive = this.vhSelfEraseCount > 0;
}

// =============================================================================
//  Status effect applied: stop this puppet from perceiving the player
// =============================================================================

@wrapMethod(NPCPuppet)
protected cb func OnStatusEffectApplied(evt: ref<ApplyStatusEffectEvent>) -> Bool {
  let result: Bool = wrappedMethod(evt);
  let player: ref<PlayerPuppet>;
  let senses: ref<SenseComponent>;

  if !IsDefined(evt) || !IsDefined(evt.staticData) {
    return result;
  };

  if !ArrayContains(evt.staticData.GameplayTags(), n"VH_SelfErase") {
    return result;
  };

  senses = this.GetSensesComponent();
  if IsDefined(senses) {
    player = GetPlayer(this.GetGame());
    if IsDefined(player) {
      senses.SetHearingEnabled(false);
      senses.SetDetectionOverwrite(player.GetEntityID());
      senses.SetDetectionAttitudeOverwrite(n"player");
    };
  };

  player = GetPlayer(this.GetGame());
  if IsDefined(player) {
    player.VH_NoteSelfErase(1);
  };

  FTLog("[XY] SelfErase applied on a target");
  return result;
}

// =============================================================================
//  Status effect removed: give the puppet its senses back
// =============================================================================

@wrapMethod(NPCPuppet)
protected cb func OnStatusEffectRemoved(evt: ref<RemoveStatusEffect>) -> Bool {
  let result: Bool = wrappedMethod(evt);
  let player: ref<PlayerPuppet>;
  let senses: ref<SenseComponent>;

  if !IsDefined(evt) || !IsDefined(evt.staticData) {
    return result;
  };

  if !ArrayContains(evt.staticData.GameplayTags(), n"VH_SelfErase") {
    return result;
  };

  player = GetPlayer(this.GetGame());
  senses = this.GetSensesComponent();

  if IsDefined(senses) && IsDefined(player) {
    senses.SetHearingEnabled(true);
    senses.RemoveDetectionOverwrite(player.GetEntityID());
    senses.RemoveDetectionAttitudeOverwrite(n"player");
    senses.ReevaluateDetectionOverwrite(player);
  };

  if IsDefined(player) {
    player.VH_NoteSelfErase(-1);
  };

  FTLog("[XY] SelfErase removed from a target");
  return result;
}

// =============================================================================
//  Trace suppression (approach from "No Reveal Position")
//  IsAwarenessBumpingAllowed matches on the tag, so it needs no timers either.
// =============================================================================

@wrapMethod(QuickHackableQueueHelper)
public final static func IsAwarenessBumpingAllowed(target: ref<ScriptedPuppet>) -> Bool {
  if IsDefined(target) && StatusEffectHelper.HasStatusEffectWithTagConst(target, VH_Defs.SelfEraseTag()) {
    return false;
  };
  return wrappedMethod(target);
}

@wrapMethod(NPCPuppet)
public final static func RevealPlayerPositionIfNeeded(
  ownerPuppet: wref<ScriptedPuppet>,
  playerID: EntityID,
  opt isPrevention: Bool
) -> Bool {
  let player: ref<PlayerPuppet>;

  if IsDefined(ownerPuppet) && EntityID.IsDefined(playerID) {
    player = GameInstance.FindEntityByID(ownerPuppet.GetGame(), playerID) as PlayerPuppet;
    if IsDefined(player) && player.vhSelfEraseActive {
      return false;
    };
  };
  return wrappedMethod(ownerPuppet, playerID, isPrevention);
}

@wrapMethod(QuickHackableHelper)
public final static func WillHackRevealPlayer(
  playerRef: ref<PlayerPuppet>,
  targetRecordId: TweakDBID,
  action: ref<ScriptableDeviceAction>,
  opt programItemID: ItemID
) -> Bool {
  if IsDefined(playerRef) && playerRef.vhSelfEraseActive {
    return false;
  };
  return wrappedMethod(playerRef, targetRecordId, action, programItemID);
}

// =============================================================================
//  Hack Diffusion
// =============================================================================

@addMethod(PlayerPuppet)
public func VH_ExecuteHackSpread(source: ref<GameObject>) -> Void {
  let effects: array<ref<StatusEffect>>;
  let records: array<TweakDBID>;
  let targets: array<ref<GameObject>>;
  let record: ref<StatusEffect_Record>;
  let i: Int32;
  let j: Int32;

  if !IsDefined(source) {
    return;
  };

  GameInstance.GetStatusEffectSystem(this.GetGame()).GetAppliedEffects(source.GetEntityID(), effects);
  i = 0;
  while i < ArraySize(effects) {
    record = effects[i].GetRecord();
    if this.VH_IsSpreadableEffect(record) {
      ArrayPush(records, record.GetID());
    };
    i += 1;
  };

  if ArraySize(records) <= 0 {
    FTLog("[XY] HackSpread: source has no spreadable quickhack effects");
    return;
  };

  this.VH_CollectSpreadTargets(source, targets);
  FTLog("[XY] HackSpread: effects=" + IntToString(ArraySize(records)) + " targets=" + IntToString(ArraySize(targets)));

  i = 0;
  while i < ArraySize(targets) && i < VH_Defs.SpreadMaxTargets() {
    j = 0;
    while j < ArraySize(records) {
      // ApplyStatusEffect fires NPCPuppet.OnStatusEffectApplied, so any copied
      // Self-Erase sets up its own suppression without extra work here.
      StatusEffectHelper.ApplyStatusEffect(targets[i], records[j], this.GetEntityID());
      j += 1;
    };
    i += 1;
  };

  FTLog("[XY] HackSpread: applied to " + IntToString(i) + " targets");
}

@addMethod(PlayerPuppet)
private func VH_IsSpreadableEffect(record: ref<StatusEffect_Record>) -> Bool {
  let tags: array<CName>;
  let id: TweakDBID;

  if !IsDefined(record) {
    return false;
  };

  id = record.GetID();

  if id == t"BaseStatusEffect.VH_SelfErase" {
    return true;
  };
  if id == t"BaseStatusEffect.VH_SelfEraseLvl2" {
    return true;
  };
  if id == t"BaseStatusEffect.VH_SelfEraseLvl3" {
    return true;
  };
  if id == t"BaseStatusEffect.WasQuickHacked" {
    return false;
  };
  if id == t"BaseStatusEffect.QuickHackUploaded" {
    return false;
  };

  tags = record.GameplayTags();
  return ArrayContains(tags, n"Quickhack");
}

@addMethod(PlayerPuppet)
private func VH_CollectSpreadTargets(source: ref<GameObject>, targets: script_ref<array<ref<GameObject>>>) -> Void {
  let npcs: array<ref<NPCPuppet>>;
  let centerPosition: Vector4;
  let puppetCount: Int32;
  let i: Int32;

  centerPosition = source.GetWorldPosition();

  npcs = source.GetNPCsAroundObject(VH_Defs.SpreadRadius());
  i = 0;
  while i < ArraySize(npcs) {
    this.VH_TryAddSpreadTarget(targets, npcs[i], source, centerPosition);
    i += 1;
  };

  this.VH_CollectByQuery(targets, source, centerPosition, false);
  puppetCount = ArraySize(Deref(targets));
  this.VH_CollectByQuery(targets, source, centerPosition, true);

  FTLog("[XY] HackSpread targets: npcsAround=" + IntToString(ArraySize(npcs))
    + " puppets=" + IntToString(puppetCount)
    + " devices=" + IntToString(ArraySize(Deref(targets)) - puppetCount)
    + " total=" + IntToString(ArraySize(Deref(targets))));
}

@addMethod(PlayerPuppet)
private func VH_CollectByQuery(
  targets: script_ref<array<ref<GameObject>>>,
  source: ref<GameObject>,
  centerPosition: Vector4,
  wantDevice: Bool
) -> Void {
  let parts: array<TS_TargetPartInfo>;
  let query: TargetSearchQuery;
  let targetingComponent: ref<TargetingComponent>;
  let entity: ref<Entity>;
  let i: Int32;

  query.testedSet = TargetingSet.Complete;
  if wantDevice {
    query.searchFilter = TSF_And(
      TSF_All(TSFMV.Obj_Device | TSFMV.St_QuickHackable),
      TSF_Not(TSFMV.Obj_Player)
    );
  } else {
    query.searchFilter = TSF_And(
      TSF_All(TSFMV.Obj_Puppet | TSFMV.St_QuickHackable),
      TSF_Not(TSFMV.Obj_Player)
    );
  };
  query.maxDistance = Vector4.Distance(this.GetWorldPosition(), centerPosition) + VH_Defs.SpreadRadius() + 5.0;
  query.filterObjectByDistance = true;
  query.includeSecondaryTargets = false;
  query.ignoreInstigator = true;

  GameInstance.GetTargetingSystem(this.GetGame()).GetTargetParts(this, query, parts);

  if ArraySize(parts) > 200 {
    return;
  };

  i = 0;
  while i < ArraySize(parts) {
    targetingComponent = TS_TargetPartInfo.GetComponent(parts[i]);
    if IsDefined(targetingComponent) {
      entity = targetingComponent.GetEntity();
      this.VH_TryAddSpreadTarget(targets, entity as GameObject, source, centerPosition);
    };
    i += 1;
  };
}

@addMethod(PlayerPuppet)
private func VH_TryAddSpreadTarget(
  targets: script_ref<array<ref<GameObject>>>,
  candidate: ref<GameObject>,
  source: ref<GameObject>,
  centerPosition: Vector4
) -> Void {
  let puppet: ref<ScriptedPuppet>;
  let i: Int32;

  if !IsDefined(candidate) || !IsDefined(source) {
    return;
  };
  if ArraySize(Deref(targets)) >= VH_Defs.SpreadMaxTargets() {
    return;
  };
  if candidate.IsPlayer() {
    return;
  };
  if candidate.GetEntityID() == source.GetEntityID() {
    return;
  };
  if Vector4.Distance(centerPosition, candidate.GetWorldPosition()) > VH_Defs.SpreadRadius() {
    return;
  };

  puppet = candidate as ScriptedPuppet;
  if IsDefined(puppet) && puppet.IsDead() {
    return;
  };

  i = 0;
  while i < ArraySize(Deref(targets)) {
    if Deref(targets)[i].GetEntityID() == candidate.GetEntityID() {
      return;
    };
    i += 1;
  };

  ArrayPush(Deref(targets), candidate);
}

// =============================================================================
//  Upload completion -> dispatch Hack Diffusion
// =============================================================================

@addField(QuickHackUploadListener)
private let vhUploadHandled: Bool;

@wrapMethod(QuickHackUploadListener)
protected func SendUploadFinishedEvent() -> Void {
  let player: ref<PlayerPuppet>;
  let target: ref<GameObject>;
  let record: wref<ObjectAction_Record>;
  let actionName: CName;

  wrappedMethod();

  if this.vhUploadHandled || !IsDefined(this.m_action) {
    return;
  };
  this.vhUploadHandled = true;

  if !this.m_action.IsQuickHack() || this.m_action.m_isTargetDead {
    return;
  };

  record = this.m_action.GetObjectActionRecord();
  player = this.m_action.GetExecutor() as PlayerPuppet;
  target = GameInstance.FindEntityByID(this.m_gameInstance, this.m_action.GetRequesterID()) as GameObject;

  if !IsDefined(record) || !IsDefined(player) || !IsDefined(target) {
    return;
  };

  actionName = record.ActionName();

  if Equals(actionName, n"VH_HackSpread") || Equals(actionName, n"VH_HackSpreadDevice") {
    player.VH_ExecuteHackSpread(target);
  };
}

// =============================================================================
//  Attacking a target breaks Self-Erase on that target only
//  (removing the effect fires OnStatusEffectRemoved, which restores its senses)
// =============================================================================

@wrapMethod(ScriptedPuppet)
public func PuppetDamagePipelineFinalized(evt: ref<gameHitEvent>) -> Void {
  wrappedMethod(evt);

  if !IsDefined(evt) || !IsDefined(evt.attackData) {
    return;
  };

  // Damage over time does not count as "the player attacked it".
  if Equals(evt.attackData.GetAttackType(), gamedataAttackType.Effect) {
    return;
  };

  if !IsDefined(evt.attackData.GetInstigator()) || !evt.attackData.GetInstigator().IsPlayer() {
    return;
  };

  if StatusEffectHelper.HasStatusEffectWithTagConst(this, VH_Defs.SelfEraseTag()) {
    StatusEffectHelper.RemoveStatusEffectsWithTag(this, VH_Defs.SelfEraseTag());
  };
}
