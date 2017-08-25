from docutils import nodes
import json
from datetime import datetime
import os
import logging
import shutil


def row_col_maker(app, fromdocname, all_needs, need_info, need_key, make_ref=False, ref_lookup=False):
    """
    Creates and returns a column.

    :param app: current sphinx app
    :param fromdocname: current document
    :param all_needs: Dictionary of all need objects
    :param need_info: need_info object, which stores all related need data
    :param need_key: The key to access the needed data from need_info
    :param make_ref: If true, creates a reference for the given data in need_key
    :param ref_lookup: If true, it uses the data to lookup for a related need and uses its data to create the reference
    :return: column object (nodes.entry)
    """
    row_col = nodes.entry()
    para_col = nodes.paragraph()

    if need_info[need_key] is not None:
        if not isinstance(need_info[need_key], list):
            data = [need_info[need_key]]
        else:
            data = need_info[need_key]

        for index, datum in enumerate(data):
            text_col = nodes.Text(datum, datum)
            if make_ref or ref_lookup:
                try:
                    ref_col = nodes.reference("", "")
                    if not ref_lookup:
                        ref_col['refuri'] = app.builder.get_relative_uri(fromdocname, need_info['docname'])
                        ref_col['refuri'] += "#" + datum
                    else:
                        temp_need = all_needs[datum]
                        ref_col['refuri'] = app.builder.get_relative_uri(fromdocname, temp_need['docname'])
                        ref_col['refuri'] += "#" + temp_need["id"]

                except KeyError:
                    para_col += text_col
                else:
                    ref_col.append(text_col)
                    para_col += ref_col
            else:
                para_col += text_col

            if index + 1 < len(data):
                para_col += nodes.emphasis("; ", "; ")

        row_col += para_col
    return row_col


def status_sorter(a):
    """
    Helper function to sort string elements, which can be None, too.
    :param a: element, which gets sorted
    :return:
    """
    if not a["status"]:
        return ""
    return a["status"]


def rstjinja(app, docname, source):
    """
    Render our pages as a jinja template for fancy templating goodness.
    """
    # Make sure we're outputting HTML
    if app.builder.format != 'html':
        return
    src = source[0]
    rendered = app.builder.templates.render_string(
        src, app.config.html_context
    )
    source[0] = rendered


class NeedsList:
    def __init__(self, config, outdir):
        self.log = logging.getLogger(__name__)
        self.config = config
        self.outdir = outdir
        self.current_version = config.version
        self.project = config.project
        self.needs_list = {
            "project": self.project,
            "current_version": self.current_version,
            "created": "",
            "versions": {}}

    def add_need(self, version, title, need_id, need_type, need_type_name=None,
                 description=None, status=None, tags=None, links=None):
        if version not in self.needs_list["versions"].keys():
            self.needs_list["versions"][version] = {"created": "",
                                                    "needs_amount": 0,
                                                    "needs": {}}

        if "needs" not in self.needs_list["versions"][version].keys():
            self.needs_list["versions"][version]["needs"] = {}

        self.needs_list["versions"][version]["created"] = datetime.now().isoformat()
        self.needs_list["versions"][version]["needs"][need_id] = {"title": title,
                                                                  "id": need_id,
                                                                  "type": need_type,
                                                                  "type_name": need_type_name,
                                                                  "description": description,
                                                                  "status": status,
                                                                  "tags": tags,
                                                                  "links": links}
        self.needs_list["versions"][version]["needs_amount"] = len(self.needs_list["versions"][version]["needs"])

    def wipe_version(self, version):
        if version in self.needs_list["versions"].keys():
            del (self.needs_list["versions"][version])

    def write_json(self, file=None):
        # We need to rewrite some data, because this kind of data gets overwritten during needs.json import.
        self.needs_list["created"] = datetime.now().isoformat()
        self.needs_list["current_version"] = self.current_version
        self.needs_list["project"] = self.project

        needs_json = json.dumps(self.needs_list, indent=4, sort_keys=True)
        file = os.path.join(self.outdir, "needs.json")

        # if file is None:
        #     file = getattr(self.config, "needs_file", "needs.json")
        with open(file, "w") as needs_file:
            needs_file.write(needs_json)

        doc_tree_folder = os.path.join(self.outdir, ".doctrees")
        if os.path.exists(doc_tree_folder):
            shutil.rmtree(doc_tree_folder)

    def load_json(self, file=None):
        if file is None:
            file = getattr(self.config, "needs_file", "needs.json")
        if not os.path.exists(file):
            self.log.warning("Could not load needs json file {0}".format(file))
        else:
            with open(file, "r") as needs_file:
                needs_file_content = needs_file.read()
            try:
                needs_list = json.loads(needs_file_content)
            except json.JSONDecodeError:
                self.log.warning("Could not decode json file {0}".format(file))
            else:
                self.needs_list = needs_list
