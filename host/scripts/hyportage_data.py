#!/usr/bin/python

import core_data

import smt_encoding

######################################################################
# KEYWORDS MANIPULATION
######################################################################


def get_core_keyword(keyword):
	if (keyword[0] in ['-', '~']) and (keyword[1] != '*'): return keyword[1:]
	elif keyword[0] != '*': return keyword


def keywords_get_core_set(keywords):
	res = {get_core_keyword(keyword) for keyword in keywords}
	res.discard(None)
	return res


##

######################################################################
# DEPENDENCIES MANIPULATION
######################################################################


def dependencies_create(): return {}


def dependencies_add_pattern(raw_dependencies, pattern):
	if pattern not in raw_dependencies: raw_dependencies[pattern] = {}


def dependencies_add_pattern_use(raw_dependencies, pattern, use, is_required):
	mapping = raw_dependencies[pattern]
	if is_required:
		mapping[use] = is_required
	elif use not in mapping:
		mapping[use] = is_required


def dependencies_get_patterns(raw_dependencies): return raw_dependencies.keys()


######################################################################
# SPL AND MSPL MANIPULATION
######################################################################

class SPL(object):
	def __init__(
			self, eapi,
			name, core, deprecated,
			fm_local, fm_combined,
			dependencies, required_iuses_local, keywords_list,
			iuses_default, use_manipulation):
		self.eapi                    = eapi
		self.name                    = name
		self.core                    = core
		self.slots                   = core_data.spl_core_get_slot(core), core_data.spl_core_get_subslot(core)
		self.deprecated              = deprecated
		self.fm_local                = fm_local               # the part of the feature model related to local features, i.e., portage's REQUIRED_USE
		self.fm_combined             = fm_combined            # the part of the feature model relatd to external dependencies, i.e., portage's DEPEND + RDEPEND + PDEPEND
		self.smt_constraint          = None                   # translation of the full feature model into z3 constraints
		self.dependencies            = dependencies           # mapping from pattern dependencies to list of features they must have declared
		self.required_iuses_local    = required_iuses_local   # list of local features mentioned in local constraints
		self.required_iuses_external = {}                     # list of features that must be declared in this spl
		self.required_iuses          = None
		self.iuses_default           = iuses_default          # list of features declared in this spl by default
		self.iuses_full              = None                   # previous list extended with features implicitly declared by portage
		self.use_manipulation        = use_manipulation  # default use selection
		self.use_selection_full      = None                   # use selection considering default portage information
		self.use_selection_smt      = None
		self.unmasked                = None                   # if portage states that this spl is masked or not
		self.keywords_list           = keywords_list          # list of architectures valid for this spl
		self.installable             = None
		self.is_stable               = None                   # boolean stating if this spl can be installed by default on the current architecture
		self.visited                 = False                  # if the spl was visited in a graph traversal
		# self.has_several_parents   = False                  # if there are two paths to access this spl during graph traversal

	def __hash__(self): return hash(self.name)

	def __eq__(self, other):
		if isinstance(other, SPL):
			return self.name == other.name
		else:
			return False

	def update_required_iuses_external(self, features, pattern):
		res = False
		for feature in features:
			if feature in self.required_iuses_external:
				self.required_iuses_external[feature].add(pattern)
			else:
				self.required_iuses_external[feature] = {pattern}
				res = True
		return res

	def smt(self, id_repository):
		if self.installable:
			return self.smt_constraint
		else: return [smt_encoding.smt_to_string(smt_encoding.get_smt_not_spl_name(id_repository, self.name))]

	def smt_use_selection(self, id_repository, config):
		if self.use_selection_smt is None:
			use_useful = self.required_iuses & self.iuses_full
			self.use_selection_full = config.mspl_config.get_use_flags(
				self.core, self.unmasked, self.is_stable, self.use_manipulation)
			use_selection_core = self.use_selection_full & use_useful
			self.use_selection_smt = smt_encoding.convert_use_flag_selection(
				id_repository, self.name, use_useful, use_selection_core)
		return self.use_selection_smt



def spl_get_name(spl): return spl.name
def spl_get_group_name(spl): return core_data.spl_core_get_spl_group_name(spl.core)
def spl_get_slot(spl): return core_data.spl_core_get_slot(spl.core)
def spl_get_subslot(spl): return core_data.spl_core_get_subslot(spl.core)
def spl_get_slots(spl): return spl.slots
def spl_get_version(spl): return core_data.spl_core_get_version(spl.core)
def spl_get_version_full(spl): return core_data.spl_core_get_version_full(spl.core)
def spl_get_dependencies(spl): return spl.dependencies
def spl_is_deprecated(spl): return spl.deprecated


def spl_get_fm_local(spl): return spl.fm_local
def spl_get_fm_combined(spl): return spl.fm_combined
def spl_get_smt_constraint(spl): return spl.smt_constraint


def spl_get_required_iuses_local(spl): return spl.required_iuses_local
def spl_get_required_iuses(spl): return spl.required_iuses


def spl_get_keywords_list(spl): return spl.keywords_list
def spl_get_keywords_default(spl): return spl.keywords_default


def spl_get_iuses_default(spl): return spl.iuses_default
def spl_get_iuses_full(spl): return spl.iuses_full


def spl_get_use_selection_default(spl): return spl.use_selection_default


def spl_is_installable(spl): return spl.installable


def spl_is_visited(spl): return spl.visited

##


def spl_set_keywords_default(spl, keywords): spl.keywords_default = keywords
def spl_set_keywords_profile(spl, keywords): spl.keywords_profile = keywords
def spl_set_iuses_profile(spl, new_iuses): spl.iuses_profile = new_iuses
def spl_set_use_selection_profile(spl, new_use_selection): spl.use_selection_profile = new_use_selection
def spl_set_mask_profile(spl, new_mask): spl.mask_profile = new_mask


def spl_set_keywords_user(spl, keywords): spl.keywords_user = keywords
def spl_set_iuses_user(spl, new_iuses): spl.iuses_user = new_iuses
def spl_set_use_selection_user(spl, new_use_selection): spl.use_selection_user = new_use_selection
def spl_set_mask_user(spl, new_mask): spl.mask_user = new_mask


def spl_set_smt_constraint(spl, smt_constraint): spl.smt_constraint = smt_constraint


##

def mspl_create(): return {}


def mspl_add_spl(mspl, spl):
	mspl[spl_get_name(spl)] = spl


def mspl_remove_spl(mspl, spl):
	mspl.pop(spl_get_name(spl))


def mspl_update_spl(mspl, old_spl, new_spl):
	mspl[spl_get_name(old_spl)] = new_spl


######################################################################
# SPL GROUP MANIPULATION
######################################################################


class SPLGroup(object):
	def __init__(self, group_name, spl):
		self.name = group_name                            # name of the group
		self.references = [spl]                           # list of spls contained in this group
		self.slots_mapping = {spl_get_slots(spl): [spl]}  # mapping listings all spls stored in one slot
		self.smt_constraint = None                        # z3 constraint encoding this group

	def add_spl(self, spl):
		self.references.append(spl)
		slots = spl_get_slots(spl)
		if slots in self.slots_mapping:
			self.slots_mapping[slots].append(spl)
		else:
			self.slots_mapping[slots] = [spl]

	def replace_spl(self, old_spl, new_spl):
		self.add_spl(new_spl)
		self.remove_spl(old_spl)

	def remove_spl(self, spl):
		self.references.remove(spl)
		slots = spl_get_slots(spl)
		if len(self.slots_mapping[slots]) == 1:
			self.slots_mapping.pop(slots)
		else:
			self.slots_mapping[slots].remove(spl)

	def __iter__(self): return iter(self.references)


def spl_groups_create(): return {}


def spl_groups_add_spl(spl_groups, spl):
	group_name, version_full, spl_name = (spl_get_group_name(spl), spl_get_version_full(spl), spl_get_name(spl))
	group = spl_groups.get(group_name)
	if group:
		group.add_spl(spl)
		return None
	else:
		group = SPLGroup(group_name, spl)
		spl_groups[group_name] = group
		return group


def spl_groups_replace_spl(spl_groups, old_spl, new_spl):
	group = spl_groups.get(spl_get_group_name(new_spl))
	group.replace_spl(old_spl, new_spl)


def spl_groups_remove_spl(spl_groups, spl):
	group_name = spl_get_group_name(spl)
	group = spl_groups.get(group_name)
	if group:
		if len(spl_group_get_references(group)) == 1:
			return spl_groups.pop(group_name)
		else:
			group.remove_spl(spl)
			return None


def spl_group_get_references(spl_group): return spl_group.references


def spl_group_get_name(spl_group): return spl_group.name


def spl_group_get_slot_mapping(spl_group): return spl_group.slots_mapping


def spl_group_set_smt_constraint(spl_group, smt_constraint): spl_group.smt_constraint = smt_constraint


def spl_group_get_smt_constraint(spl_group): return spl_group.smt_constraint

