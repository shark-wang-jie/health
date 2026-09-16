import copy
import importlib
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import record_tools as daily
import build_monthly_summary as monthly


def example(day='2026-09-09', weight=91.8):
    r=daily.new_record(day,weight,day,weight)
    r['food_coverage']='confirmed_complete'
    r['training_status']='reported_training'
    r['training_coverage']='confirmed_complete'
    r['record_status']='final';r['food_log_closed']=True;r['closure_basis']='用户明确确认结束'
    r['intake_entries']=[daily.food_from_catalog('shaxian_two_skinless_legs','lunch')]
    r['exercise_entries']=[{'id':'strength','event_id':'session-strength','type':'传统力量训练','duration':'35分22秒','energy_scope':'session_active','source':'Apple Watch','active_kcal':273,'total_kcal':335}]
    r['daily_summary']=daily.calculate(r)
    return r

class DailyTests(unittest.TestCase):
    def test_formula_and_no_double_margin(self):
        r=example();s=r['daily_summary']
        self.assertAlmostEqual(s['intake_kcal_booked'],973.5)
        self.assertAlmostEqual(s['intake_kcal_base_estimate'],885)
        self.assertAlmostEqual(s['exercise_adjusted_kcal'],204.75)
        self.assertAlmostEqual(s['tdee_kcal_estimate'],2447.85)
        self.assertAlmostEqual(s['estimated_deficit_kcal'],1474.35)
        self.assertEqual(s,daily.calculate(r));daily.validate(r)
    def test_planned_excluded_and_ids_rejected(self):
        r=example();e=copy.deepcopy(r['intake_entries'][0]);e.update(id='plan',status='planned');r['intake_entries'].append(e)
        self.assertEqual(daily.calculate(r)['intake_kcal_booked'],973.5000000000001)
        e['id']='lunch'
        with self.assertRaises(ValueError):daily.calculate(r)
    def test_label_margin_and_repeated_margin_rejected(self):
        r=example();e=daily.food_from_catalog('yogurt_zero_fat_300g','y');r['intake_entries']=[e]
        daily.calculate(r)
        e['kcal_booked']+=10;e['kcal_range'][1]+=10
        with self.assertRaises(ValueError):daily.calculate(r)
        r=example();r['intake_entries'][0]['margin']['already_in_base']=True
        with self.assertRaises(ValueError):daily.calculate(r)
    def test_unknown_not_rest_and_missing_training(self):
        r=daily.new_record('2026-09-09',91.8,'2026-09-08')
        self.assertIsNone(r['morning_weight_kg']);self.assertTrue(r['daily_summary']['target_is_provisional'])
        r=example();r['exercise_entries'][0]['active_kcal']=None
        self.assertTrue(daily.calculate(r)['energy_estimate_provisional'])
        r['training_status']='confirmed_rest'
        with self.assertRaises(ValueError):daily.calculate(r)
    def test_corruption_scope_bmr_and_nonfinite(self):
        for mutation in [lambda r:r['daily_summary'].update(intake_kcal_booked=1),lambda r:r['profile_snapshot'].update(bmr_kcal=2500),lambda r:r['exercise_entries'][0].update(energy_scope='all_day_active'),lambda r:r['intake_entries'][0].update(kcal_base_estimate=float('nan'))]:
            r=example();mutation(r)
            with self.assertRaises(ValueError):daily.validate(r)
    def test_no_false_zero_micronutrients(self):
        s=example()['daily_summary']
        self.assertIsNone(s['fiber_g_known_sum']);self.assertFalse(s['fiber_g_coverage_complete'])
    def test_final_not_necessarily_complete(self):
        r=example();r['food_coverage']='partial';r['daily_summary']=daily.calculate(r)
        daily.validate(r);self.assertTrue(r['daily_summary']['energy_estimate_provisional'])
    def test_atomic_write_and_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json';daily.save_json(p,example());daily.validate(json.loads(p.read_text()))
    def test_open_or_training_incomplete_has_no_final_deficit(self):
        r=example();r['record_status']='open';r['food_log_closed']=False
        self.assertIsNone(daily.calculate(r)['completed_day_estimated_deficit_kcal'])
        r=example();r['training_coverage']='partial'
        self.assertIsNone(daily.calculate(r)['completed_day_estimated_deficit_kcal'])
    def test_duplicate_device_session_rejected(self):
        r=example();r['exercise_entries'][0]['event_id']='same-session'
        e=copy.deepcopy(r['exercise_entries'][0]);e['id']='bike-device';r['exercise_entries'].append(e)
        with self.assertRaises(ValueError):daily.calculate(r)
    def test_missing_macro_range_stays_unknown(self):
        r=example();r['intake_entries']=[daily.food_from_catalog('milk_260ml','milk')]
        s=daily.calculate(r);self.assertIsNone(s['protein_g_range'])
        self.assertEqual(s['protein_g_estimate'],8)
    def test_plan_changes_are_inherited(self):
        plan=json.loads((daily.ROOT/'current_plan.json').read_text())
        plan['targets']['training_day_intake_kcal_range']=[2000,2100];plan['profile']['age']=28
        r=daily.new_record('2026-09-09',91.8,'2026-09-08',plan=plan)
        r['training_status']='reported_training';r['exercise_entries']=example()['exercise_entries']
        self.assertEqual(daily.calculate(r)['intake_target_kcal_range'],[2000,2100])
        self.assertEqual(r['profile_snapshot']['age'],28)
    def test_catalog_scaling(self):
        e=daily.food_from_catalog('shaxian_two_skinless_legs','lunch',.5)
        self.assertAlmostEqual(e['kcal_booked'],486.75)
        r=example();r['intake_entries']=[e];daily.calculate(r)

class ReviewTests(unittest.TestCase):
    def records(self):
        start=date(2026,8,20)
        return [example((start+timedelta(days=i)).isoformat(),92-i*.4/7) for i in range(28)]
    def test_cross_month_and_calibration(self):
        r=daily.rolling_review(self.records(),'2026-09-16')
        self.assertTrue(r['calibration_eligible']);self.assertAlmostEqual(r['weekly_weight_loss_kg_approx'],.4)
        self.assertEqual([w['valid_measurements'] for w in r['weeks']],[7]*4)
    def test_missing_and_method_change_blocks_calibration(self):
        records=self.records();records.pop(2)
        self.assertFalse(daily.rolling_review(records,'2026-09-16')['calibration_eligible'])
        records=self.records();records[1]['food_estimation_policy']='changed'
        self.assertFalse(daily.rolling_review(records,'2026-09-16')['calibration_eligible'])
    def test_calibration_uses_real_dates_and_aligned_intake(self):
        records=self.records()
        for i in (4,5,6,7,8,9):records[i]['morning_weight_kg']=None
        result=daily.rolling_review(records,'2026-09-16')
        self.assertTrue(result['calibration_eligible'])
        self.assertAlmostEqual(result['weekly_weight_loss_kg_approx'],.4)
        self.assertEqual(result['calibration_intake_period']['days'],27)
    def test_trend_context_blocks_automatic_calibration(self):
        records=self.records();records[0]['trend_context']=['刚开始使用肌酸，体重水分可能变化']
        self.assertFalse(daily.rolling_review(records,'2026-09-16')['calibration_eligible'])
    def test_unresolved_and_sparse_weights(self):
        records=self.records();records[1]['missing_sections']=['份量待确认'];records[1]['daily_summary']=daily.calculate(records[1])
        self.assertFalse(daily.rolling_review(records,'2026-09-16')['calibration_eligible'])
        records=self.records()
        for r in records[:4]:r['morning_weight_kg']=None
        self.assertFalse(daily.rolling_review(records,'2026-09-16')['calibration_eligible'])

class MonthlyTests(unittest.TestCase):
    def test_legacy_compatibility_and_separate_algorithm(self):
        old=json.loads((daily.ROOT/'daily/2026-09/2026-09-08.json').read_text())
        s=monthly.build_summary('2026-09',[old,example()])
        self.assertEqual(s['conservative_deficit_summary']['total_conservative_deficit_kcal'],728)
        self.assertEqual(len(s['energy_summary_by_algorithm']),2)
        self.assertEqual(s['nutrition_summary']['fat_g_point_summary']['days_with_data'],2)
        self.assertEqual(s['nutrition_summary']['new_intake_target_comparison']['below'],1)
    def test_incomplete_excluded_from_target(self):
        r=example();r['food_coverage']='partial';r['daily_summary']=daily.calculate(r)
        s=monthly.build_summary('2026-09',[r])
        self.assertEqual(s['nutrition_summary']['new_intake_target_comparison']['excluded_incomplete_days'],1)
    def test_provisional_balance_excluded_from_month_deficit(self):
        r=example();r['training_coverage']='unknown';r['daily_summary']=daily.calculate(r)
        s=monthly.build_summary('2026-09',[r])['energy_summary_by_algorithm']['tdee_v1']
        self.assertIsNone(s['total_estimated_deficit_kcal']);self.assertEqual(s['excluded_provisional_days'],1)
    def test_missing_new_schema_rejected(self):
        r=example();r.pop('schema_version')
        with self.assertRaises(ValueError):monthly.daily_metrics(r)
    def test_duration_formats(self):
        for value,expected in (('35分22秒',35+22/60),('35:22',35+22/60),('00:35:22',35+22/60),('45分钟',45),('约50分钟',50),('约1小时10分',70)):
            self.assertAlmostEqual(monthly.parse_duration_minutes({'duration':value}),expected)
        self.assertAlmostEqual(monthly.parse_duration_minutes({'duration_seconds':2700}),45)
        self.assertAlmostEqual(monthly.parse_duration_minutes({'duration_min':50}),50)
    def test_month_boundary(self):
        self.assertFalse(monthly.month_is_finished('2026-09',date(2026,9,30)))
        self.assertTrue(monthly.month_is_finished('2026-09',date(2026,10,1)))
    def test_all_existing_months_readonly(self):
        for month in ('2026-07','2026-08','2026-09'):
            records=monthly.load_month(month);s=monthly.build_summary(month,records)
            self.assertEqual(s['coverage']['recorded_days'],len(records))
            expected=sorted({'legacy_bmr_plus_exercise' if r.get('schema_version')!=3 else 'tdee_v1' for r in records})
            self.assertEqual(list(s['energy_summary_by_algorithm']),expected)

class EvidenceWorkflowTests(unittest.TestCase):
    def test_base_macros_separate_from_margin(self):
        r=example();summary=r['daily_summary']
        self.assertAlmostEqual(summary['base_macro_estimates']['fat_g'],27)
        self.assertAlmostEqual(summary['food_margin_kcal'],88.5)
        self.assertAlmostEqual(summary['completed_day_base_intake_balance_kcal']-summary['completed_day_estimated_deficit_kcal'],88.5)
    def test_weight_trend_survives_old_or_missing_food(self):
        records=ReviewTests().records()
        records[0].pop('schema_version')
        result=daily.rolling_review(records,'2026-09-16')
        self.assertTrue(result['weight_trend']['available'])
        self.assertFalse(result['calibration_eligible'])
    def test_watch_data_not_needed_for_intake_weight_calibration(self):
        records=ReviewTests().records()
        for record in records:
            record['exercise_entries'][0]['active_kcal']=None
            record['daily_summary']=daily.calculate(record)
        result=daily.rolling_review(records,'2026-09-16')
        self.assertTrue(result['calibration_eligible'])
        self.assertFalse(result['exercise_model_comparison_available'])
    def test_effective_plan_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'plans').mkdir()
            for name,effective,revision in [('old','2026-09-09',1),('current','2026-10-01',2)]:
                plan={'version':name,'effective_from':effective,'revision':revision}
                path=root/'current_plan.json' if name=='current' else root/'plans/old.json'
                path.write_text(json.dumps(plan))
            self.assertEqual(daily.select_plan('2026-09-12',root)['version'],'old')
            self.assertEqual(daily.select_plan('2026-10-12',root)['version'],'current')
            with self.assertRaises(ValueError):daily.select_plan('2026-09-08',root)
    def test_report_suppresses_unfinished_deficit(self):
        r=example();r['record_status']='open';r['food_log_closed']=False;r['daily_summary']=daily.calculate(r)
        report=daily.render_daily_report(r)
        self.assertIn('全天最终缺口暂不报告',report)
        self.assertNotIn('估算缺口约',report)
    def test_planned_food_not_counted_in_month(self):
        r=example();entry=copy.deepcopy(r['intake_entries'][0]);entry.update(id='future',status='planned');r['intake_entries'].append(entry);r['daily_summary']=daily.calculate(r)
        summary=monthly.build_summary('2026-09',[r])
        self.assertEqual(summary['nutrition_summary']['total_meal_entries'],1)
    def test_strength_working_sets_and_equipment_separation(self):
        r=example();r['exercise_entries'][0]['resistance_sets']=[
            {'set_type':'warmup'},
            {'set_type':'working','exercise_name':'卧推','equipment':'杠铃','load_basis':'总重','load_kg':60,'reps':8,'rir':2},
            {'set_type':'working','exercise_name':'卧推','equipment':'史密斯','load_basis':'配重','load_kg':60,'reps':8,'rir':None}]
        result=daily.strength_progress([r]);self.assertEqual(len(result['exercises']),2)
        self.assertEqual(sum(x['reported_working_sets'] for x in result['exercises']),2)
        daily.calculate(r)
    def test_month_command_does_not_overwrite_history(self):
        import subprocess
        path=daily.ROOT/'daily/2026-08/2026-08-summary.json';before=path.read_bytes()
        result=subprocess.run([sys.executable,str(daily.ROOT/'build_monthly_summary.py'),'2026-08'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('已存在',result.stdout);self.assertEqual(before,path.read_bytes())

if __name__=='__main__':unittest.main()
