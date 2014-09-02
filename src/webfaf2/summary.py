from operator import itemgetter
from pyfaf.storage import (Build,
                           Report,
                           OpSysComponent,
                           OpSysRelease,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           Package,
                           ReportOpSysRelease,
                           ReportArch,
                           ReportPackage,
                           ReportSelinuxMode,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportUnknownPackage,
                           )
from pyfaf.queries import get_history_target
from flask import Blueprint, render_template, request, abort
from sqlalchemy import literal, desc, func


summary = Blueprint("summary", __name__)

from webfaf2 import db
from forms import SummaryForm
from utils import date_iterator


@summary.route("/")
def index():
    summary_form = SummaryForm(request.args)

    reports = []
    if summary_form.validate():
        hist_table, hist_field = get_history_target(summary_form.resolution.data)
        #opsysrelease_ids = [osr.id for osr in (summary_form.opsysreleases.data or [])]
        arch_ids = [arch.id for arch in (summary_form.arch.data or [])]
        component_ids = [comp.id for comp in (summary_form.components.data or [])]
        (since_date, to_date) = summary_form.daterange.data

        if summary_form.opsysreleases.data:
            opsysreleases = summary_form.opsysreleases.data
        else:
            opsysreleases = db.session.query(OpSysRelease).all()

        for osr in opsysreleases:
            counts = (db.session.query(hist_field.label("time"),
                                       func.sum(hist_table.count).label("count"))
                                .group_by(hist_field)
                                .order_by(hist_field))

            counts = counts.filter(hist_table.opsysrelease_id == osr.id)

            if component_ids:
                counts = (counts.join(Report)
                                .filter(Report.component_id.in_(component_ids)))

            counts = (counts.filter(hist_field >= since_date)
                            .filter(hist_field <= to_date))

            counts = counts.all()

            dates = set(date_iterator(since_date, summary_form.resolution.data, to_date))
            for time, count in counts:
                dates.remove(time)
            for date in dates:
                counts.append((date, 0))
            counts = sorted(counts, key=itemgetter(0))
            reports.append((str(osr), counts))

    return render_template("summary/index.html",
                           summary_form=summary_form,
                           reports=reports,
                           resolution=summary_form.resolution.data[0])
