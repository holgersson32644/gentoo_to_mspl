#!/usr/bin/python

import sys
import os
import os.path
import logging
import subprocess
import bz2
import cPickle
import logging

import core_data


__author__ = "Michael Lienhardt"
__copyright__ = "Copyright 2017, Michael Lienhardt"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Michael Lienhardt"
__email__ = "michael lienhardt@laposte.net"
__status__ = "Prototype"

"""
This file extracts USE flags declarations, USE flag selection and Package visibility information (mask and keywords)
 that are specified outside the .ebuild files. 

As shown in the documentation, this information is structured in three parts:
 - the one that is 


We assume that the .ebuild file does not declare any variables that are used in
 the later construction of the IUSE and USE variables.
This assumption is motivated by efficiency
  (we would otherwise have to load the portage profile independently for every packages),
 and is supported by the fact that egencache produces files without any annex variables to use in later stages.

We also assume that the EAPI is 6 system-wide.
Indeed, dealing with specific EAPI does not seem useful.
"""


# todo: I need to refactor this file to take in account the information I got on USE flag declarations and selection.
# I thus need to structure the configuration in three parts: one that is


######################################################################
# FILE PATHS
######################################################################

# input

input_dir_portage = os.path.realpath("/usr/portage/metadata/md5-cache/")
input_dir_portage_installed = os.path.realpath("/var/db/pkg/")

input_file_profile_base = os.path.realpath("/usr/portage/profiles")
input_file_profile_selected = os.path.realpath("/etc/portage/make.profile")

input_dir_user_configuration = os.path.realpath("/etc/portage/")
input_file_make_conf = os.path.join(input_dir_user_configuration, "make.conf")
input_file_user_world = os.path.realpath("/var/lib/portage/world")

input_file_keyword_list = os.path.realpath("/usr/portage/profiles/arch.list")


script_dir = os.path.dirname(os.path.abspath(__file__))

#logging.info("location portage tree: " + input_dir_portage)
#logging.info("location installed packages: " + input_dir_portage_installed)
#logging.info("location user profile: " + input_file_profile_base)
#logging.info("location selected profile: " + input_file_profile_selected)
#logging.info("location base user config: " + input_dir_user_configuration)
#logging.info("location make.conf file: " + input_file_make_conf)
#logging.info("location world file: " + input_file_user_world)
#logging.info("location list of keywords: " + input_file_keyword_list)

# output

non_concurrent_map = map  # the different load processes must be done in sequence


######################################################################
# 1. UTILITY FUNCTIONS FOR LOADING A CONFIGURATION
######################################################################


######################################################################
# 1.1. BASH ENVIRONMENT MANIPULATION

def environment_create_from_script_output(out):
	"""
	Create a dictionary from the output of the "set" (in posix mode) function
	Note that the value of some variable contain \n characters, which explains the tricks used here.
	:param out: the string containing the result of "set"
	:return: the dictionary mapping all the variables present in the output to their value
	"""
	environment = {}
	# variables to deal with shell values being on severa lines
	variable = None
	value = None
	for line in out.splitlines(): # to deal with multiple-line variables
		if value:
			value = value + line
		else:
			array = line.split("=", 1)
			variable = array[0]
			value = array[1]
		if (len(value) == 0) or ((len(value) > 0) and ((value[0] != "'") or (value[-1] == "'"))):
			if (len(value) > 0) and (value[0] == "'"):
				value = value[1:-1]
			environment[variable] = value
			value = None
	return environment


def environment_extract_info(environment):
	"""
	Extracts the important information from an environment: the IUSE, USE, ARCH and ACCEPT_KEYWORDS variables
	:param environment: the input environment
	:return: the tuple containing the values of the important variables
	"""
	use_selection = core_data.SetManipulation()
	use_selection.add_all(environment.get('USE', "").split())
	use_declaration_eapi4 = set(environment.get('IUSE_EAPI_4', "").split())
	use_declaration_eapi5 = set(environment.get('IUSE_EAPI_5', "").split())
	use_declaration_hidden_from_user = set(environment.get('FLAT_PROFILE_ONLY_VARIABLES', "").split())
	arch = environment.get('ARCH')
	accept_keywords = core_data.SetManipulation()
	accept_keywords.add_all(environment.get('ACCEPT_KEYWORDS', "").split())
	return (
		use_selection, use_declaration_eapi4, use_declaration_eapi5,
		use_declaration_hidden_from_user, arch, accept_keywords
	)


##

script_load_make_defaults = os.path.join(script_dir, "load_make_defaults.sh")
def make_defaults_load_file(filename, environment):
	process = subprocess.Popen(["/bin/bash", script_load_make_defaults, filename], stdout=subprocess.PIPE, env=environment)
	out, err = process.communicate()
	return environment_create_from_script_output(out)


##

def load_make_defaults(filename, environment):
	new_environment = make_defaults_load_file(filename, environment)
	return new_environment, environment_extract_info(new_environment)


def get_loading_order(environment):
	new_environment = make_defaults_load_file(input_file_make_conf, environment)
	return list(reversed(new_environment.get('USE_ORDER', "env:pkg:conf:defaults:pkginternal:repo:env.d").split(':')))


######################################################################
# 1.2. USE*, PACKAGE.USE* and PACKAGES MANIPULATION

def parse_configuration_file(filename):
	res = []
	if os.path.isfile(filename):
		with open(filename, 'r') as f:
			for line in f:
				line = line[:-1]  # remove trailing endline
				line = line.split("#", 1)[0]  # remove comment
				line.strip()  # remove starting and trailing spaces
				if len(line) != 0:
					res.append(line)
	return res


def load_use_file(filename):
	res = core_data.SetManipulation()
	res.add_all(parse_configuration_file(filename))
	return res


def load_package_use_file(filename):
	res = core_data.SetManipulationPattern()
	for line in parse_configuration_file(filename):
		els = line.split()
		set_manipulation = core_data.SetManipulation()
		set_manipulation.add_all(els[1:])
		res.add(core_data.pattern_create_from_atom(els[0]), set_manipulation)
	return res


def load_package_mask_file(filename):
	res = core_data.PatternListManipulation()
	res.add_all(parse_configuration_file(filename))
	return res


def load_package_keywords_file(filename):
	res = core_data.SetManipulationPattern()
	for line in parse_configuration_file(filename):
		els = line.split()
		set_manipulation = core_data.SetManipulation()
		set_manipulation.add_all(els[1:])
		res.add(core_data.pattern_create_from_atom(els[0]), set_manipulation)
	return res


def load_packages_file(filename):
	res = core_data.dictSet()
	for line in parse_configuration_file(filename):
		if line[0] == "*":
			res.add("system", core_data.pattern_create_from_atom(line[1:]))
		else:
			res.add("profile", core_data.pattern_create_from_atom(line))
	return res


######################################################################
# 2. UTILITY FUNCTIONS FOR LOADING A PROFILE
######################################################################

# list of use files: use.force   use.mask   use.stable.force   use.stable.mask
# list of package.use files: package.use   package.use.force   package.use.mask
#    package.use.stable.force   package.use.stable.mask
# there is just one make.defaults

# The use.* are global, i.e., they are merged between layers, and applied globally.
# They override declarations made locally to a package

# the order in which they are loaded is as follows:
# package.use use.force use.mask make.defaults

def load_profile_layer(path, environment):
	#######################
	# use* files
	# use.force
	path_use_force = os.path.join(path, "use.force")
	use_force = load_use_file(path_use_force)
	# use.mask
	path_use_mask = os.path.join(path, "use.mask")
	use_mask = load_use_file(path_use_mask)
	# use.stable.force
	path_use_stable_force = os.path.join(path, "use.stable.force")
	use_stable_force = load_use_file(path_use_stable_force)
	# use.stable.mask
	path_use_stable_mask = os.path.join(path, "use.stable.mask")
	use_stable_mask = load_use_file(path_use_stable_mask)
	#######################
	# package.use* files
	# package.use
	path_package_use = os.path.join(path, "package.use")
	package_use = load_package_use_file(path_package_use)
	# package.use.force
	path_package_use_force = os.path.join(path, "package.use.force")
	package_use_force = load_package_use_file(path_package_use_force)
	# package.use.mask
	path_package_use_mask = os.path.join(path, "package.use.mask")
	package_use_mask = load_package_use_file(path_package_use_mask)
	# package.use.stable.force
	path_package_use_stable_force = os.path.join(path, "package.use.stable.force")
	package_use_stable_force = load_package_use_file(path_package_use_stable_force)
	# package.use.stable.mask
	path_package_use_stable_mask = os.path.join(path, "package.use.stable.mask")
	package_use_stable_mask = load_package_use_file(path_package_use_stable_mask)
	#######################
	# make.defaults file
	path_make_defaults = os.path.join(path, "make.defaults")
	if os.path.exists(path_make_defaults):
		new_environment, info = load_make_defaults(path_make_defaults, environment)
		make_defaults_use_selection = info[0]
		make_defaults_use_declaration_eapi4, make_defaults_use_declaration_eapi5 = info[1], info[2]
		make_defaults_use_declaration_hidden_from_user = info[3]
		make_defaults_arch, make_defaults_accept_keywords = info[4], info[5]
		make_defaults_use_declaration_eapi4.update(use_force.get_elements())
		make_defaults_use_declaration_eapi4.update(use_mask.get_elements())
		make_defaults_use_declaration_eapi4.update(core_data.SetManipulation().add_all(
				new_environment.get('BOOTSTRAP_USE', "").split()).get_elements())
	else:
		new_environment = environment
		make_defaults_use_selection = core_data.SetManipulation()
		make_defaults_use_declaration_eapi4, make_defaults_use_declaration_eapi5 = set(), set()
		make_defaults_use_declaration_hidden_from_user = set()
		make_defaults_arch, make_defaults_accept_keywords = None, core_data.SetManipulation()
	#######################
	# packages (required patterns)
	path_package_required = os.path.join(path, "packages")
	package_required = core_data.dictSet()
	if os.path.exists(path_package_required):
		for line in parse_configuration_file(path_package_required):
			if line[0] == "*":
				package_required.add("system", core_data.pattern_create_from_atom(line[1:]))
			else:
				package_required.add("profile", core_data.pattern_create_from_atom(line))
	#######################
	# package.provided (packages implicitly provided)
	path_package_provided = os.path.join(path, "package.provided")
	if os.path.exists(path_package_provided):
		package_provided = set(parse_configuration_file(path_package_provided))
	else:
		package_provided = set()
	#######################
	# package.mask and package.unmask (packages masking)
	path_package_mask = os.path.join(path, "package.mask")
	package_mask = load_package_mask_file(path_package_mask)
	path_package_unmask = os.path.join(path, "package.unmask")
	package_unmask = load_package_mask_file(path_package_unmask)
	#######################
	# package.keywords or package.accept_keywords
	path_package_keywords = os.path.join(path, "package.keywords")
	package_keywords = load_package_keywords_file(path_package_keywords)
	path_package_accept_keywords = os.path.join(path, "package.accept_keywords")
	package_accept_keywords = load_package_keywords_file(path_package_accept_keywords)

	#######################
	# return the result
	res_use_selection_config = core_data.UseSelectionConfig(
		make_defaults_use_selection, use_force, use_mask, use_stable_force, use_stable_mask,
		package_use, package_use_force, package_use_mask, package_use_stable_force, package_use_stable_mask
	)
	res = core_data.MSPLConfig(
		make_defaults_arch,
		make_defaults_use_declaration_eapi4, make_defaults_use_declaration_eapi5, make_defaults_use_declaration_hidden_from_user,
		res_use_selection_config,
		package_required, package_provided,	package_mask, package_unmask,
		make_defaults_accept_keywords, package_keywords, package_accept_keywords
	)
	return new_environment, res


def combine_profile_layer_data(data1, data2):
	config = data1[1]
	config.update(data2[1])
	return data2[0], config


def load_profile(path, environment):
	path_parent = os.path.join(path, "parent")
	if os.path.exists(path_parent):
		sub_profiles = parse_configuration_file(path_parent)
		configs = []
		for sub_profile in sub_profiles:
			environment, config = load_profile(os.path.join(path, sub_profile), environment)
			configs.append(config)
		environment, config = load_profile_layer(path, environment)
		configs.append(config)
		config = configs[0]
		for data in configs[1:]:
			config.update(data)
		return environment, config
	else:
		return load_profile_layer(path, environment)


######################################################################
# 3. UTILITY FUNCTIONS FOR LOADING /ETC/PORTAGE/ CONFIGURATION
######################################################################

def get_user_configuration_files_in_path(path):
	if os.path.isfile(path):
		return [ path ]
	elif os.path.isdir(path):
		print("list of files: " + unicode(os.listdir(path)))
		filename_list = filter(os.path.isfile, [os.path.join(path, filename) for filename in os.listdir(path)])
		filename_list.sort()
		return filename_list
	else: return []


def get_user_configuration(environment):
	# first is loaded the profile, which is then updated with local definitions
	# 1. package.use
	files_package_use = get_user_configuration_files_in_path(
		os.path.join(input_dir_user_configuration, "package.use"))
	pattern_use_selection = core_data.SetManipulationPattern()
	for filename in files_package_use:
		pattern_use_selection.update(load_package_use_file(filename))

	# 2. package.accept_keywords / package.keywords
	files_package_accept_keywords = get_user_configuration_files_in_path(
		os.path.join(input_dir_user_configuration, "package.accept_keywords"))
	pattern_accept_keywords = core_data.SetManipulationPattern()
	for filename in files_package_accept_keywords:
		pattern_accept_keywords.update(load_package_keywords_file(filename))

	files_package_keywords = get_user_configuration_files_in_path(
		os.path.join(input_dir_user_configuration, "package.keywords"))
	pattern_keywords = core_data.SetManipulationPattern()
	for filename in files_package_keywords:
		pattern_keywords.update(load_package_keywords_file(filename))

	# 3. package.mask / package.unmask
	files_package_mask = get_user_configuration_files_in_path(os.path.join(input_dir_user_configuration, "package.mask"))
	pattern_mask = core_data.PatternListManipulation()
	for filename in files_package_mask:
		pattern_mask.update(load_package_mask_file(filename))

	files_package_unmask = get_user_configuration_files_in_path(os.path.join(input_dir_user_configuration, "package.unmask"))
	pattern_unmask = core_data.PatternListManipulation()
	for filename in files_package_unmask:
		pattern_unmask.update(load_package_mask_file(filename))

	# 6. sets
	location_sets = os.path.join(input_dir_user_configuration, "sets")
	pattern_required = core_data.dictSet()
	if os.path.isdir(location_sets):
		for filename in os.listdir(location_sets):
			for line in parse_configuration_file(os.path.join(location_sets, filename)):
				pattern_required.add(filename, core_data.pattern_create_from_atom(line))

	# 7. local profile
	location_local_profile = os.path.join(input_dir_user_configuration, "profile")
	if os.path.isdir(location_local_profile):
		environment, config = load_profile_layer(location_local_profile, environment)
		config.update_pattern_use(pattern_use_selection)
		config.update_pattern_required(pattern_required)
		config.update_pattern_mask(pattern_mask)
		config.update_pattern_unmask(pattern_unmask)
		config.update_pattern_accept_keywords(pattern_accept_keywords)
		config.update_pattern_keywords(pattern_keywords)
	else:
		use_selection_config = core_data.UseSelectionConfig(
			pattern_use=pattern_use_selection
		)
		config = core_data.MSPLConfig(
			use_selection_config=use_selection_config,
			pattern_required=pattern_required,
			pattern_mask=pattern_mask,
			pattern_unmask=pattern_unmask,
			pattern_accept_keywords=pattern_accept_keywords,
			pattern_keywords=pattern_keywords
		)

	return environment, config



######################################################################
# 4. THE SEVEN STEPS OF USE AND VISIBILITY CONSTRUCTIONS
######################################################################

# all these function have a common API: they set the data in the input config object,
#  and return the new environment

######################################################################
# 4.1. env.d

# we suppose that env-update is up-to-date
def env_d(system, environment):
	process = subprocess.Popen(["bash", "-c", "source /etc/profile.env ; /usr/bin/env"], stdout=subprocess.PIPE, env={})
	out, err = process.communicate()
	environment.update(environment_create_from_script_output(out))
	return environment


######################################################################
# 4.2. repo

def repo(system, environment):
	new_environment, mspl_config = load_profile_layer(input_file_profile_base, environment)
	system.mspl_config.update(mspl_config)
	return new_environment


######################################################################
# 4.3. pkginternal

# dealt in the translation of each individual package
def pkginternal(system, environment):
	system.close_init_phase()
	return environment


######################################################################
# 4.4. defaults

def defaults(system, environment):
	new_environment, mspl_config = load_profile(input_file_profile_selected, environment)
	system.mspl_config.update(mspl_config)
	return new_environment


######################################################################
# 4.5. conf

def conf(system, environment):
	new_environment, info = load_make_defaults(input_file_make_conf, environment)
	use_selection, use_declaration_eapi4, use_declaration_eapi5, use_declaration_hidden_from_user, arch, accept_keywords = info
	system.mspl_config.use_selection_config.use.update(use_selection)
	system.mspl_config.use_declaration_eapi4.update(use_declaration_eapi4)
	system.mspl_config.use_declaration_eapi5.update(use_declaration_eapi5)
	system.mspl_config.use_declaration_hidden_from_user.update(use_declaration_hidden_from_user)
	system.mspl_config.accept_keywords.update(accept_keywords)
	if arch:
		system.mspl_config.arch = arch
	return new_environment


######################################################################
# 4.6. pkg

def pkg(system, environment):
	new_environment, mspl_config = get_user_configuration(environment)
	system.mspl_config.update(mspl_config)
	return new_environment


######################################################################
# 4.7. env

# dealt with during the execution of the emerge command
# hopefully, the environment will always be at the end
def env(system, environment):
	return environment


######################################################################
# 4.8. mapping to construct the core configuration
config_construction_mapping = {
	'env.d': env_d,
	'repo': repo,
	'pkginternal': pkginternal,
	'defaults': defaults,
	'conf': conf,
	'pkg': pkg,
	'env': env
}


######################################################################
# 5. CONFIG OBJECT CONSTRUCTION
######################################################################

######################################################################
# loading the list of keywords, with their unstable prefix
def load_keyword_list():
	keyword_list = parse_configuration_file(input_file_keyword_list)
	keyword_list = keyword_list + ["~" + keyword for keyword in keyword_list]
	return keyword_list


def load_installed_package_uses(package_path):
	try:
		with open(os.path.join(package_path, "USE"), 'r') as f:
			uses = set(f.read().split())
		return uses
	except IOError:
		sys.stderr.write("Warning: in path \"" + package_path + "\", no file USE found\n")
		return None


def load_installed_packages():
	data = core_data.dictSet()
	for directory in os.listdir(input_dir_portage_installed):
		path = os.path.join(input_dir_portage_installed, directory)
		for package in os.listdir(path):
			package_name = directory + "/" + package
			#print("looking at " + package_name)
			complete_path = os.path.join(path, package)
			uses = load_installed_package_uses(complete_path)
			data.set(package_name, uses)
	return data


######################################################################
# load the world file
def load_world_file():
	atom_list = parse_configuration_file(input_file_user_world)
	clean_atom_list = []
	for atom in atom_list:
		if "::" in atom:
			logging.warning("the atom \"" + atom + "\" is tagged with a repository annotation. trimming it")
			clean_atom_list.append(atom.split("::", 1)[0])
		else: clean_atom_list.append(atom)
	return set(map(core_data.pattern_create_from_atom, clean_atom_list))


######################################################################
# generate the egencache files for the deprecated packages
def load_installed_package(package_path, outfile):
	eapi = None
	iuses = None
	required_use = None
	depend = None
	rdepend = None
	pdepend = None
	slots = None
	keywords = None
	license = None
	# parse "environment.bz2" in which all variables are declared
	variable = None
	value = None
	with bz2.BZ2File(os.path.join(package_path, "environment.bz2"), 'r') as f:
		for line in f.readlines(): # to deal with multiple-line variables
			line = line[:-1]
			if value:
				value = value + " " + line
			else:
				array = line.split("=", 1)
				if (len(array) == 2) and (array[0].startswith("declare")):
					variable = array[0]
					value = array[1]
				else:
					variable = None
					value = None
			if variable:
				if value[-1] == "\"":
					value = value[1:-1]
					#print(variable + " = " + value)
					# set the correct variables
					if variable.endswith("EAPI"):
						eapi = value
					if variable.endswith("IUSE_EFFECTIVE"):
						iuses = value
					elif (variable.endswith("IUSE")) and (iuses is None):
						iuses = value
					elif variable.endswith("REQUIRED_USE"):
						required_use = value
					elif variable.endswith("DEPEND"):
						depend = value
					elif variable.endswith("RDEPEND"):
						rdepend = value
					elif variable.endswith("PDEPEND"):
						pdepend = value
					elif variable.endswith("SLOT"):
						slots = value
					elif variable.endswith("KEYWORDS"):
						keywords = value
					elif variable.endswith("LICENSE"):
						license = value
					# reset the data
					variable = None
					value = None
	# 3. write file
	with open(outfile, 'w') as f:
		if eapi:
			f.write("EAPI=" + eapi + "\n")
		if iuses:
			f.write("IUSE=" + iuses + "\n")
		if required_use:
			f.write("REQUIRED_USE=" + required_use + "\n")
		if depend:
			f.write("DEPEND=" + depend + "\n")
		if rdepend:
			f.write("RDEPEND=" + rdepend + "\n")
		if pdepend:
			f.write("PDEPEND=" + pdepend + "\n")
		if slots:
			f.write("SLOT=" + slots + "\n")
		if keywords:
			f.write("KEYWORDS=" + keywords + "\n")
		if license:
			f.write("LICENSE=" + license + "\n")


def load_deprecated_packages(output_file_portage_deprecated):
	if not os.path.isdir(output_file_portage_deprecated):
		logging.error("The location  \"" + output_file_portage_deprecated + "\" does not exist or is not a folder")
		sys.exit(-1)
	# perform the update of the output_file_portage_deprecated folder
	# 1. remove useless files
	for directory in os.listdir(output_file_portage_deprecated):
		path = os.path.join(output_file_portage_deprecated, directory)
		for package in os.listdir(path):
			if not os.path.exists(os.path.join(os.path.join(input_dir_portage_installed, directory), package)):
				os.remove(os.path.join(path, package))
	# 2. add new files
	for directory in os.listdir(input_dir_portage_installed):
		path = os.path.join(input_dir_portage_installed, directory)
		for package_dir in os.listdir(path):
			# 2.1. check that this is indeed a deprecated package
			if os.path.exists(os.path.join(os.path.join(input_dir_portage, directory), package_dir)):
				continue
			# 2.2. create file if does not already exist
			new_path_dir = os.path.join(output_file_portage_deprecated, directory)
			new_path = os.path.join(new_path_dir, package_dir)
			if not os.path.exists(new_path):
				old_path = os.path.join(os.path.join(input_dir_portage_installed, directory), package_dir)
				if not os.path.exists(new_path_dir):
					os.makedirs(new_path_dir)
				load_installed_package(old_path, new_path)


######################################################################
# main function
def main(output_dir):
	# 1. construct the core configuration
	system = core_data.Config()
	environment = os.environ
	use_order = get_loading_order(environment)
	passed_env = False
	passed_pkginternal = False
	for stage in use_order:
		if stage == "pkginternal":
			passed_pkginternal = True
		if passed_env:
			logging.error("The USE_ORDER variable does not have 'env' at the end: " + str(use_order))
			sys.exit(-1)
		print("Running Stage \"" + stage + "\"")
		passed_env = stage == "env"
		environment = config_construction_mapping[stage](system, environment)
	if not passed_pkginternal:
		logging.error("The USE_ORDER variable must contain 'pkginternal': " + str(use_order))
		sys.exit(-1)

	# 2. add the keyword list, the installed packages and the world file
	system.keyword_list = load_keyword_list()
	system.installed_packages = load_installed_packages()
	system.world = load_world_file()
	system.close()

	# 3. save the config
	save_filename = os.path.join(output_dir, "config.pickle")
	if os.path.isfile(save_filename):
		with open(save_filename, 'r') as f:
			old_system = cPickle.load(f)
			system.mspl_config.set_old_config(old_system.mspl_config)
	with open(save_filename, 'w') as f:
		cPickle.dump(system, f)
	# 4. generate the egencache files for the deprecated packages
	load_deprecated_packages(os.path.join(output_dir, "packages/deprecated"))




if __name__ == "__main__":
	main(sys.argv[1])
