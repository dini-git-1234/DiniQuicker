from pathlib import Path

from utils.file_utils import save_upload_file


def _save_files(files, input_dir: Path) -> dict:
    saved = {
        "tabu": None,
        "building_plan": None,
        "rights_confirmation": None,
        "lease_document": None,
        "bylaws": None,
        "civil_admin": None,
        "mortgage_confirmation": None,
        "outside": None,
        "inside": [],
        "previous_appraisals": None,
        "sale_agreement": None,
        "rental_agreement": None,
        "arnona_form": None,
    }

    if getattr(files, "tabu", None):
        saved["tabu"] = save_upload_file(files.tabu, input_dir, "tabu")
    if getattr(files, "building_plan", None):
        saved["building_plan"] = save_upload_file(files.building_plan, input_dir, "building_plan")
    if getattr(files, "rights_confirmation", None):
        saved["rights_confirmation"] = save_upload_file(files.rights_confirmation, input_dir, "rights_confirmation")
    if getattr(files, "lease_document", None):
        saved["lease_document"] = save_upload_file(files.lease_document, input_dir, "lease_document")
    if getattr(files, "bylaws", None):
        saved["bylaws"] = save_upload_file(files.bylaws, input_dir, "bylaws")
    if getattr(files, "civil_admin", None):
        saved["civil_admin"] = save_upload_file(files.civil_admin, input_dir, "civil_admin")
    if getattr(files, "mortgage_confirmation", None):
        saved["mortgage_confirmation"] = save_upload_file(files.mortgage_confirmation, input_dir, "mortgage_confirmation")
    if getattr(files, "previous_appraisals", None):
        saved["previous_appraisals"] = save_upload_file(files.previous_appraisals, input_dir, "previous_appraisals")
    if getattr(files, "sale_agreement", None):
        saved["sale_agreement"] = save_upload_file(files.sale_agreement, input_dir, "sale_agreement")
    if getattr(files, "rental_agreement", None):
        saved["rental_agreement"] = save_upload_file(files.rental_agreement, input_dir, "rental_agreement")
    if getattr(files, "arnona_form", None):
        saved["arnona_form"] = save_upload_file(files.arnona_form, input_dir, "arnona_form")

    if getattr(files, "outside_image", None):
        saved["outside"] = save_upload_file(files.outside_image, input_dir, "outside")

    if getattr(files, "inside_images", None):
        for img in files.inside_images:
            saved["inside"].append(save_upload_file(img, input_dir, "inside"))

    return saved

